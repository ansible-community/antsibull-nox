# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox sessions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import typing as t
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import nox

from ..collection import (
    CollectionData,
    setup_collections,
    setup_current_tree,
)
from ..data_util import prepare_data_script
from ..paths import (
    create_temp_directory,
    find_data_directory,
    list_all_files,
)

# https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables#default-environment-variables
# https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
# https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
IN_CI = os.environ.get("CI") == "true"
IN_GITHUB_ACTIONS = bool(os.environ.get("GITHUB_ACTION"))
ALLOW_EDITABLE = os.environ.get("ALLOW_EDITABLE", str(not IN_CI)).lower() in (
    "1",
    "true",
)

_SESSIONS: dict[str, list[dict[str, t.Any]]] = {}


@contextmanager
def _ci_group(name: str) -> t.Iterator[None]:
    """
    Try to ensure that the output inside the context is printed in a collapsable group.

    This is highly CI system dependent, and currently only works for GitHub Actions.
    """
    if IN_GITHUB_ACTIONS:
        print(f"::group::{name}")
    yield
    if IN_GITHUB_ACTIONS:
        print("::endgroup::")


def _register(name: str, data: dict[str, t.Any]) -> None:
    if name not in _SESSIONS:
        _SESSIONS[name] = []
    _SESSIONS[name].append(data)


def install(session: nox.Session, *args: str, editable: bool = False, **kwargs):
    """
    Install Python packages.
    """
    # nox --no-venv
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn(f"No venv. Skipping installation of {args}")
        return
    # Don't install in editable mode in CI or if it's explicitly disabled.
    # This ensures that the wheel contains all of the correct files.
    if editable and ALLOW_EDITABLE:
        args = ("-e", *args)
    session.install(*args, "-U", **kwargs)


@dataclass
class CollectionSetup:
    """
    Information on the setup collections.
    """

    # The path of the ansible_collections directory where all dependent collections
    # are installed. Is currently identical to current_root, but that might change
    # or depend on options in the future.
    collections_root: Path

    # The directory in which ansible_collections can be found, as well as
    # ansible_collections/<namespace>/<name> points to a copy of the current collection.
    current_place: Path

    # The path of the ansible_collections directory that contains the current collection.
    # The following is always true:
    #   current_root == current_place / "ansible_collections"
    current_root: Path

    # Data on the current collection (as in the repository).
    current_collection: CollectionData

    # The path of the current collection inside the collection tree below current_root.
    # The following is always true:
    #   current_path == current_root / current_collection.namespace / current_collection.name
    current_path: Path

    def prefix_current_paths(self, paths: list[str]) -> list[str]:
        """
        Prefix the list of given paths with ``current_path``.
        """
        result = []
        for path in paths:
            prefixed_path = (self.current_path / path).relative_to(self.current_place)
            if prefixed_path.exists():
                result.append(str(prefixed_path))
        return result


def _run_subprocess(args: list[str]) -> tuple[bytes, bytes]:
    p = subprocess.run(args, check=True, capture_output=True)
    return p.stdout, p.stderr


def prepare_collections(
    session: nox.Session,
    *,
    install_in_site_packages: bool,
    extra_deps_files: list[str | os.PathLike] | None = None,
    extra_collections: list[str] | None = None,
    install_out_of_tree: bool = False,  # can not be used with install_in_site_packages=True
) -> CollectionSetup | None:
    """
    Install collections in site-packages.
    """
    if install_out_of_tree and install_in_site_packages:
        raise ValueError(
            "install_out_of_tree=True cannot be combined with install_in_site_packages=True"
        )
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn("No venv. Skip preparing collections...")
        return None
    if install_in_site_packages:
        purelib = (
            session.run(
                "python",
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
                silent=True,
            )
            or ""
        ).strip()
        if not purelib:
            session.warn(
                "Cannot find site-packages (probably due to install-only run)."
                " Skip preparing collections..."
            )
            return None
        place = Path(purelib)
    elif install_out_of_tree:
        place = create_temp_directory(f"antsibull-nox-{session.name}-collection-root-")
    else:
        place = Path(session.virtualenv.location) / "collection-root"
    place.mkdir(exist_ok=True)
    setup = setup_collections(
        place,
        _run_subprocess,
        extra_deps_files=extra_deps_files,
        extra_collections=extra_collections,
        with_current=False,
        global_cache_dir=session.cache_dir,
    )
    current_setup = setup_current_tree(place, setup.current_collection)
    return CollectionSetup(
        collections_root=setup.root,
        current_place=place,
        current_root=current_setup.root,
        current_collection=setup.current_collection,
        current_path=t.cast(Path, current_setup.current_path),
    )


def _run_bare_script(
    session: nox.Session,
    /,
    name: str,
    *,
    use_session_python: bool = False,
    files: list[Path] | None = None,
    extra_data: dict[str, t.Any] | None = None,
) -> None:
    if files is None:
        files = list_all_files()
    data = prepare_data_script(
        session,
        base_name=name,
        paths=files,
        extra_data=extra_data,
    )
    python = sys.executable
    env = {}
    if use_session_python:
        python = "python"
        env["PYTHONPATH"] = str(find_data_directory())
    session.run(
        python,
        find_data_directory() / f"{name}.py",
        "--data",
        data,
        external=True,
        env=env,
    )


def _compose_description(
    *,
    prefix: str | dict[t.Literal["one", "other"], str] | None = None,
    programs: dict[str, str | bool | None],
) -> str:
    parts: list[str] = []

    def add(text: str, *, comma: bool = False) -> None:
        if parts:
            if comma:
                parts.append(", ")
            else:
                parts.append(" ")
        parts.append(text)

    active_programs = [
        (program, value if isinstance(value, str) else None)
        for program, value in programs.items()
        if value not in (False, None)
    ]

    if prefix:
        if isinstance(prefix, dict):
            if len(active_programs) == 1 and "one" in prefix:
                add(prefix["one"])
            else:
                add(prefix["other"])
        else:
            add(prefix)

    for index, (program, value) in enumerate(active_programs):
        if index + 1 == len(active_programs) and index > 0:
            add("and", comma=index > 1)
        add(program, comma=index > 0 and index + 1 < len(active_programs))
        if value is not None:
            add(f"({value})")

    return "".join(parts)


def add_matrix_generator() -> None:
    """
    Add a session that generates matrixes for CI systems.
    """

    def matrix_generator(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        json_output = os.environ.get("ANTSIBULL_NOX_MATRIX_JSON")
        if json_output:
            print(f"Writing JSON output to {json_output}...")
            with open(json_output, "wt", encoding="utf-8") as f:
                f.write(json.dumps(_SESSIONS))

        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            print(f"Writing GitHub output to {github_output}...")
            with open(github_output, "at", encoding="utf-8") as f:
                for name, sessions in _SESSIONS.items():
                    f.write(f"{name}={json.dumps(sessions)}\n")

        for name, sessions in sorted(_SESSIONS.items()):
            print(f"{name} ({len(sessions)}):")
            for session_data in sessions:
                data = session_data.copy()
                session_name = data.pop("name")
                print(f"  {session_name}: {data}")

    matrix_generator.__doc__ = "Generate matrix for CI systems."
    nox.session(
        name="matrix-generator",
        python=False,
        default=False,
    )(matrix_generator)


__all__ = [
    "add_matrix_generator",
    "install",
    "prepare_collections",
]
