# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utils for creating nox sessions.
"""

from __future__ import annotations

import os
import sys
import typing as t
from contextlib import contextmanager
from pathlib import Path

import nox

from ..data_util import prepare_data_script
from ..paths import (
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
def ci_group(name: str) -> t.Iterator[None]:
    """
    Try to ensure that the output inside the context is printed in a collapsable group.

    This is highly CI system dependent, and currently only works for GitHub Actions.
    """
    if IN_GITHUB_ACTIONS:
        print(f"::group::{name}")
    yield
    if IN_GITHUB_ACTIONS:
        print("::endgroup::")


def register(name: str, data: dict[str, t.Any]) -> None:
    """
    Register a session name for matrix generation with additional data.
    """
    if name not in _SESSIONS:
        _SESSIONS[name] = []
    _SESSIONS[name].append(data)


def get_registered_sessions() -> dict[str, list[dict[str, t.Any]]]:
    """
    Return all registered sessions.
    """
    return {
        name: [session.copy() for session in sessions]
        for name, sessions in _SESSIONS.items()
    }


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


def run_bare_script(
    session: nox.Session,
    /,
    name: str,
    *,
    use_session_python: bool = False,
    files: list[Path] | None = None,
    extra_data: dict[str, t.Any] | None = None,
) -> None:
    """
    Run a bare script included in antsibull-nox's data directory.
    """
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


def compose_description(
    *,
    prefix: str | dict[t.Literal["one", "other"], str] | None = None,
    programs: dict[str, str | bool | None],
) -> str:
    """
    Compose a description for a nox session from several configurable parts.
    """
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


__all__ = [
    "ci_group",
    "compose_description",
    "get_registered_sessions",
    "install",
    "register",
    "run_bare_script",
]
