# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Generate job matrix for use in CI systems.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
import sys
import tempfile
import typing as t
from collections.abc import Iterable, Mapping
from pathlib import Path

from .ansible import AnsibleCoreVersion, parse_ansible_core_version
from .config import (
    CONFIG_FILENAME,
    load_config_from_toml,
)
from .lint_config import NOXFILE_PY
from .utils import Version

_YAML_NO_NEED_TO_ESCAPE = re.compile(r"^[a-zA-Z0-9_ .,;/()+-]+$")
_ANSIBLE_CORE_VERSION = re.compile(r"Ⓐ\s*(?:devel|milestone|\d+\.\d+)")


def _run_nox(
    args: list[str],
    *,
    env_update: Mapping[str, str] | None = None,
    env_remove: Iterable[str] | None = None,
    check_rc: bool = False,
) -> tuple[int, bytes, bytes]:
    """
    Run nox.
    """
    env = os.environ.copy()
    if env_remove:
        for ev in env_remove:
            env.pop(ev, None)
    if env_update:
        env.update(env_update)
    p = subprocess.run(
        [sys.executable, "-m", "nox"] + args,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env=env,
        check=check_rc,
    )
    return p.returncode, p.stdout, p.stderr


def get_ci_matrix(
    *,
    min_ansible_core: str | None = None,
    max_ansible_core: str | None = None,
    include_tags: str | None = None,
    exclude_tags: str | None = None,
) -> dict[str, list[dict[str, t.Any]]]:
    """
    Retrieve the CI matrix for this directory's noxfile.py, assuming it uses antsibull-nox.
    """
    cmd = ["-e", "matrix-generator", "--"]
    if min_ansible_core is not None:
        cmd.extend(["--min-ansible-core", min_ansible_core])
    if max_ansible_core is not None:
        cmd.extend(["--max-ansible-core", max_ansible_core])
    if include_tags is not None:
        cmd.extend(["--include-tags", include_tags])
    if exclude_tags is not None:
        cmd.extend(["--exclude-tags", exclude_tags])
    fh, path = tempfile.mkstemp()
    try:
        os.close(fh)
        _run_nox(
            cmd,
            env_remove=["GITHUB_OUTPUT"],
            env_update={"ANTSIBULL_NOX_MATRIX_JSON": path},
        )
        with open(path, "rb") as f:
            data = json.load(f)
    finally:
        os.unlink(path)

    if not isinstance(data, Mapping):
        raise ValueError(f"Unexpected matrix output: {type(data)} instead of mapping")

    result = {}
    for name, sessions in data.items():
        if not isinstance(sessions, list):
            raise ValueError(
                f"Unexpected matrix output for category {name!r}: {type(sessions)} instead of list"
            )
        session_list: list[dict[str, t.Any]] = []
        result[name] = session_list
        for index, session in enumerate(sessions):
            if not isinstance(session, Mapping):
                raise ValueError(
                    f"Unexpected matrix output for category {name!r}:"
                    f" list element {index + 1} has type {type(session)}"
                )
            if not isinstance(session.get("name"), str):
                raise ValueError(
                    f"Unexpected matrix output for category {name!r}:"
                    f" list element {index + 1} has no name: {session!r}"
                )
            session_list.append(dict(session))
    return result


@dataclasses.dataclass
class _Session:
    title: str
    name: str


@dataclasses.dataclass
class _Group:
    title: str
    name: str
    dependencies: list[str]
    sessions: list[_Session]


def _ansible_core_name(version: AnsibleCoreVersion | None = None) -> str:
    if version == Version.parse("2.9"):
        return "Ansible"
    if version == Version.parse("2.10"):
        return "ansible-base"
    return "ansible-core"


def _get_title(
    session: dict[str, t.Any], *, with_ansible_core_version: bool, convert_py: bool
) -> str:
    display_name = session.get("display-name")
    if display_name:
        if with_ansible_core_version:
            ansible_core: str | None = session.get("ansible-core")
            ansible_core_name = _ansible_core_name(
                parse_ansible_core_version(ansible_core) if ansible_core else None
            )
            display_name = display_name.replace("Ⓐ", f"{ansible_core_name} ")
        else:
            display_name = _ANSIBLE_CORE_VERSION.sub("", display_name).lstrip(" +/,")
        if convert_py:
            display_name = display_name.replace("py", "Python ")
        display_name = display_name.replace("+", " + ")
    return display_name or session["name"]


def _convert_sessions(
    sessions: list[dict[str, t.Any]],
    *,
    with_ansible_core_version: bool,
    convert_py: bool = False,
) -> list[_Session]:
    result = []
    for session in sessions:
        result.append(
            _Session(
                name=session["name"],
                title=_get_title(
                    session,
                    with_ansible_core_version=with_ansible_core_version,
                    convert_py=convert_py,
                ),
            )
        )
    return result


def _create_unit_groups(
    data: dict[str, list[dict[str, t.Any]]], *, split_up_unit_tests: bool
) -> list[_Group]:
    if "units" not in data:
        return []
    if not split_up_unit_tests:
        return [
            _Group(
                name="units",
                title="Unit tests",
                dependencies=[],
                sessions=_convert_sessions(
                    data["units"], with_ansible_core_version=True
                ),
            )
        ]

    unit_sessions: dict[str, list[dict[str, t.Any]]] = {}
    for session in data["units"]:
        ansible_core: str | None = session.get("ansible-core")
        if ansible_core is None:
            raise ValueError("Found unit test session without ansible-core information")
        unit_session_list = unit_sessions.get(ansible_core)
        if unit_session_list is None:
            unit_session_list = []
            unit_sessions[ansible_core] = unit_session_list
        unit_session_list.append(session)
    result = []
    for ansible_core, sessions in unit_sessions.items():
        result.append(
            _Group(
                name=f"units_{ansible_core.replace('-', '_').replace('.', '_')}",
                title=f"Units {ansible_core}",
                dependencies=[],
                sessions=_convert_sessions(
                    sessions, with_ansible_core_version=False, convert_py=True
                ),
            )
        )
    return result


def _create_integration_groups(data: dict[str, list[dict[str, t.Any]]]) -> list[_Group]:
    if "integration" not in data:
        return []
    int_sessions: dict[
        tuple[t.Literal["docker", "remote", "other"], str], list[dict[str, t.Any]]
    ] = {}
    for session in data["integration"]:
        ansible_core: str | None = session.get("ansible-core")
        if ansible_core is None:
            raise ValueError(
                "Found integration test session without ansible-core information"
            )
        tags: list[str] = session.get("tags") or []
        is_docker = "docker" in tags
        is_remote = "remote" in tags
        key: tuple[t.Literal["docker", "remote", "other"], str] = (
            "remote" if is_remote else "docker" if is_docker else "other",
            ansible_core,
        )
        int_session_list = int_sessions.get(key)
        if int_session_list is None:
            int_session_list = []
            int_sessions[key] = int_session_list
        int_session_list.append(session)
    result = []
    for what in sorted({w for w, _ in int_sessions}):
        for (w, ansible_core), sessions in int_sessions.items():
            if what != w:
                continue
            result.append(
                _Group(
                    name=f"{what}_{ansible_core.replace('-', '_').replace('.', '_')}",
                    title=f"{what.title()} {ansible_core}",
                    dependencies=[],
                    sessions=_convert_sessions(
                        sessions, with_ansible_core_version=False
                    ),
                )
            )
    return result


def _create_groups(
    data: dict[str, list[dict[str, t.Any]]], *, split_up_unit_tests: bool = False
) -> list[_Group]:
    result = []
    if "sanity" in data:
        result.append(
            _Group(
                name="sanity",
                title="Sanity",
                dependencies=[],
                sessions=_convert_sessions(
                    data["sanity"], with_ansible_core_version=True
                ),
            )
        )
    result.extend(_create_unit_groups(data, split_up_unit_tests=split_up_unit_tests))
    result.extend(_create_integration_groups(data))
    return result


def _get_azp_definition_content(path: Path) -> tuple[list[str], list[str], list[str]]:
    state = 0
    data: tuple[list[str], list[str], list[str]] = [], [], []
    with path.open("rt", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            next_state = state
            if state == 0 and line.startswith("stages:"):
                next_state = 1
            if state == 1 and line and not line.startswith(("#", " ")):
                state = next_state = 2
            data[state].append(line)
            state = next_state
    if state == 0:
        raise ValueError(f"Cannot find stage definitions in {path}")
    return data


def _write_azp_definition(path: Path, content: list[str]) -> None:
    with path.open("wt", encoding="utf-8") as f:
        f.write("\n".join(content) + "\n")


_YAML_ESCAPES: dict[str, str] = {
    "\n": r"\n",
    "\\": r"\\",
    '"': r"\"",
    "'": r"\'",
}


def _escape_yaml(value: str) -> str:
    if _YAML_NO_NEED_TO_ESCAPE.match(value):
        # If this is parsable as a float, quote it
        try:
            float(value)
        except ValueError:
            return value
    result = ['"']
    for c in value:
        repl = _YAML_ESCAPES.get(c)
        if repl is not None:
            result.append(repl)
        elif ord(c) < 32:
            result.append(f"\\u{hex(ord(c))[2:].rjust(4, '0')}")
        else:
            result.append(c)
    result.append('"')
    return "".join(result)


def update_azp_config(
    *,
    min_ansible_core: str | None = None,
    max_ansible_core: str | None = None,
    include_tags: str | None = None,
    exclude_tags: str | None = None,
) -> bool:
    """
    Update AZP config.

    Return true if the config changed.
    """
    azp_definition: Path = Path(".azure-pipelines/azure-pipelines.yml")
    for expected_file in (
        CONFIG_FILENAME,
        NOXFILE_PY,
        azp_definition,
    ):
        if not os.path.isfile(expected_file):
            raise ValueError(f"{expected_file} does not exist or is not a file")

    config_path = Path(CONFIG_FILENAME)
    config = load_config_from_toml(config_path)
    split_up_unit_tests = False
    if config.sessions.ansible_test_units:
        split_up_unit_tests = config.sessions.ansible_test_units.split_by_python_version

    data = get_ci_matrix(
        min_ansible_core=min_ansible_core,
        max_ansible_core=max_ansible_core,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
    )

    pre, old_main, post = _get_azp_definition_content(azp_definition)
    main: list[str] = []

    groups = _create_groups(data, split_up_unit_tests=split_up_unit_tests)
    for group in groups:
        main.append(f"  - stage: {_escape_yaml(group.name)}")
        main.append(f"    displayName: {_escape_yaml(group.title)}")
        if group.dependencies:
            main.append("    dependsOn:")
            for dep in group.dependencies:
                main.append(f"      - {_escape_yaml(dep)}")
        else:
            main.append("    dependsOn: []")
        main.append("    variables:")
        main.append("      entryPoint: tests/utils/shippable/nox.sh")
        main.append("    jobs:")
        main.append("      - template: templates/matrix.yml")
        main.append("        parameters:")
        main.append("          targets:")
        for session in group.sessions:
            main.append(f"            - name: {_escape_yaml(session.title)}")
            main.append(f"              test: {_escape_yaml(session.name)}")
        main.append("")
    main.append("  - stage: Summary")
    main.append("    condition: succeededOrFailed()")
    if groups:
        main.append("    dependsOn:")
        for group in groups:
            main.append(f"      - {_escape_yaml(group.name)}")
    else:
        main.append("    dependsOn: []")
    main.append("    jobs:")
    main.append("      - template: templates/coverage.yml")

    _write_azp_definition(azp_definition, pre + main + post)
    return old_main != main
