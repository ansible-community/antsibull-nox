# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Generate job matrix for use in CI systems.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import typing as t
from collections.abc import Sequence

import nox

from ..ansible import get_actual_ansible_core_version, parse_ansible_core_version
from ..utils import Version
from .utils import get_registered_sessions, parse_args


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nox -e matrix-generator --",
        description="Generate matrix for CI systems.",
        exit_on_error=False,
    )

    parser.add_argument("--min-ansible-core", help="Minimum ansible-core version")
    parser.add_argument("--max-ansible-core", help="Maximum ansible-core version")
    parser.add_argument(
        "--include-tags", help="Comma-separated list of tags that have to be present"
    )
    parser.add_argument(
        "--exclude-tags", help="Comma-separated list of tags that must not be present"
    )

    return parser


def _parse_version(
    version: str | None, *, option_name: str, session: nox.Session
) -> Version | None:
    if version is None:
        return None
    try:
        return get_actual_ansible_core_version(parse_ansible_core_version(version))
    except ValueError as exc:
        return session.error(f"{option_name}: {exc}")


def _ensure_sequence(value: str | Sequence[str] | None) -> Sequence[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return value
    return []


def _filter(
    sessions: list[dict[str, t.Any]],
    *,
    min_ansible_core: Version | None,
    max_ansible_core: Version | None,
    include_tags: list[str] | None,
    exclude_tags: list[str] | None,
) -> list[dict[str, t.Any]]:
    result = []
    for session in sessions:
        ansible_core = session.get("ansible-core")
        if isinstance(ansible_core, str):
            version = get_actual_ansible_core_version(
                parse_ansible_core_version(ansible_core)
            )
            if min_ansible_core is not None and version < min_ansible_core:
                continue
            if max_ansible_core is not None and version > max_ansible_core:
                continue
        tags = _ensure_sequence(session.get("tags"))
        if include_tags and not all(tag in tags for tag in include_tags):
            continue
        if exclude_tags and any(tag in tags for tag in exclude_tags):
            continue
        result.append(session)
    return result


def _split(tag_string: str | None) -> t.Generator[str]:
    if tag_string is None:
        return
    for part in tag_string.split(","):
        part = part.strip()
        if part:
            yield part


def add_matrix_generator() -> None:
    """
    Add a session that generates matrixes for CI systems.
    """

    def matrix_generator(
        session: nox.Session,
    ) -> None:
        parser = _create_parser()
        args = parse_args(parser=parser, session=session)
        if args is None:
            return

        min_ansible_core = _parse_version(
            args.min_ansible_core, option_name="--min-ansible-core", session=session
        )
        max_ansible_core = _parse_version(
            args.max_ansible_core, option_name="--max-ansible-core", session=session
        )
        include_tags = list(_split(args.include_tags))
        exclude_tags = list(_split(args.exclude_tags))
        print(include_tags, exclude_tags)

        registered_sessions = get_registered_sessions()
        for key, sessions in list(registered_sessions.items()):
            filtered_sessions = _filter(
                sessions,
                min_ansible_core=min_ansible_core,
                max_ansible_core=max_ansible_core,
                include_tags=include_tags,
                exclude_tags=exclude_tags,
            )
            if filtered_sessions:
                registered_sessions[key] = filtered_sessions
            else:
                del registered_sessions[key]

        json_output = os.environ.get("ANTSIBULL_NOX_MATRIX_JSON")
        if json_output:
            print(f"Writing JSON output to {json_output}...")
            with open(json_output, "wt", encoding="utf-8") as f:
                f.write(json.dumps(registered_sessions))

        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            print(f"Writing GitHub output to {github_output}...")
            with open(github_output, "at", encoding="utf-8") as f:
                for name, sessions in registered_sessions.items():
                    f.write(f"{name}={json.dumps(sessions)}\n")

        for name, sessions in sorted(registered_sessions.items()):
            print(f"{name} ({len(sessions)}):")
            for session_data in sessions:
                data = session_data.copy()
                session_name = data.pop("name")
                print(f"  {session_name}: {data}")

        sys.stdout.flush()

    matrix_generator.__doc__ = "Generate matrix for CI systems."
    nox.session(
        name="matrix-generator",
        python=False,
        default=False,
    )(matrix_generator)


__all__ = [
    "add_matrix_generator",
]
