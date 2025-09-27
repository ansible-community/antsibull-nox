# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utils for creating nox sessions.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import typing as t
from contextlib import contextmanager

import nox
from nox.logger import OUTPUT as nox_OUTPUT

# https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables#default-environment-variables
# https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
# https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
IN_CI = os.environ.get("CI") == "true"
IN_GITHUB_ACTIONS = bool(os.environ.get("GITHUB_ACTION"))

_SESSIONS: dict[str, list[dict[str, t.Any]]] = {}


def nox_has_verbosity() -> bool:
    """
    Determine whether nox is run with verbosity enabled.
    """
    logger = logging.getLogger()
    return logger.level <= nox_OUTPUT


@contextmanager
def silence_run_verbosity() -> t.Iterator[None]:
    """
    When using session.run() with silent=True, nox will log the output
    if -v is used. Using this context manager prevents printing the output.
    """
    logger = logging.getLogger()
    original_level = logger.level
    try:
        logger.setLevel(max(nox_OUTPUT + 1, original_level))
        yield
    finally:
        logger.setLevel(original_level)


@contextmanager
def ci_group(name: str) -> t.Iterator[tuple[str, bool]]:
    """
    Try to ensure that the output inside the context is printed in a collapsable group.

    This is highly CI system dependent, and currently only works for GitHub Actions.
    """
    is_collapsing = False
    if IN_GITHUB_ACTIONS:
        print(f"::group::{name}")
        sys.stdout.flush()
        is_collapsing = True
    yield ("  " if is_collapsing else "", is_collapsing)
    if IN_GITHUB_ACTIONS:
        print("::endgroup::")
        sys.stdout.flush()


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


def parse_args(
    *,
    session: nox.Session,
    parser: argparse.ArgumentParser,
) -> argparse.Namespace | None:
    """
    Parse arguments for a session.

    The ``ArgumentParser`` object should be created with ``exit_on_error=False``.

    Return ``None`` if the session should exit immediately, or a ``argparse.Namespace``
    object with the parsed arguments.
    """
    try:
        return parser.parse_args(session.posargs)
    except argparse.ArgumentError as exc:
        # session.error() never returns, but pylint doesn't seem to know that,
        # so we use the 'return function()' pattern...
        return session.error(str(exc))
    except SystemExit as exc:
        if exc.code in (0, None):
            return None
        if isinstance(exc.code, str):
            session.error(exc.code)
        return session.error("Error")


def normalize_session_name(name: str) -> str:
    """
    Replace/remove not allowed characters in session names.
    """
    # So far, I'm only aware of '/'.
    return name.replace("/", "-")


__all__ = [
    "ci_group",
    "compose_description",
    "get_registered_sessions",
    "normalize_session_name",
    "nox_has_verbosity",
    "register",
    "silence_run_verbosity",
]
