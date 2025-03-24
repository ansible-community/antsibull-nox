# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utility code for scripts in data.
"""

from __future__ import annotations

import json
import sys
import typing as t
from pathlib import Path

import nox


def setup() -> tuple[list[str], dict[str, t.Any]]:
    """
    Fetch list of paths and potential extra configuration.

    First thing to call in an extra sanity check script in data/.
    """
    if len(sys.argv) == 3 and sys.argv[1] == "--data":
        # Preferred way: load information from JSON file
        path = sys.argv[2]
        try:
            with open(path, "rb") as f:
                data = json.load(f)
        except Exception as exc:
            raise ValueError(f"Error while reading JSON from {path}") from exc
        try:
            paths = get_list_of_strings(data, "paths")
        except ValueError as exc:
            raise ValueError(f"Invalid JSON content in {path}: {exc}") from exc
        data.pop("paths")
        return paths, data
    if len(sys.argv) >= 2:
        # It's also possible to pass a list of paths on the command line, to simplify
        # testing these scripts.
        return sys.argv[1:], {}
    # Alternatively one can pass a list of files from stdin, for example by piping
    # the output of 'git ls-files' into this script. This is also for testing these
    # scripts.
    return sys.stdin.read().splitlines(), {}


def get_list_of_strings(
    data: dict[str, t.Any],
    key: str,
    *,
    default: list[str] | None = None,
) -> list[str]:
    """
    Retrieves a list of strings from key ``key`` of the JSON object ``data``.

    If ``default`` is set to a list, a missing key results in this value being returned.
    """
    sentinel = object()
    value = data.get(key, sentinel)
    if value is sentinel:
        if default is not None:
            return default
        raise ValueError(f"{key!r} is not a present")
    if not isinstance(value, list):
        raise ValueError(f"{key!r} is not a list, but {type(key)}")
    if not all(isinstance(entry, str) for entry in value):
        raise ValueError(f"{key!r} is not a list of strings")
    return t.cast(list[str], value)


def get_bool(
    data: dict[str, t.Any],
    key: str,
    *,
    default: bool | None = None,
) -> bool:
    """
    Retrieves a boolean from key ``key`` of the JSON object ``data``.

    If ``default`` is set to a boolean, a missing key results in this value being returned.
    """
    sentinel = object()
    value = data.get(key, sentinel)
    if value is sentinel:
        if default is not None:
            return default
        raise ValueError(f"{key!r} is not a present")
    if not isinstance(value, bool):
        raise ValueError(f"{key!r} is not a bool, but {type(key)}")
    return value


def prepare_data_script(
    session: nox.Session,
    *,
    base_name: str,
    paths: list[Path],
    extra_data: dict[str, t.Any] | None = None,
) -> Path:
    """
    Prepare a data JSON file for the extra sanity check scripts.
    """
    cwd = Path.cwd()
    data = {}
    data["paths"] = [str(path.relative_to(cwd)) for path in paths]
    if extra_data:
        data.update(extra_data)
    file = Path(session.create_tmp()) / f"{base_name}-data.json"
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return file
