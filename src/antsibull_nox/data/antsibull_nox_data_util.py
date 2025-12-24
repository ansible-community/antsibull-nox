# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utility code for scripts in data.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import typing as t
from collections.abc import Mapping


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
        if paths is None:
            raise ValueError(f"Broken JSON content in {path}: path is missing")
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


if sys.version_info < (3, 13):
    _T = t.TypeVar("_T")
else:
    _T = t.TypeVar("_T", default=None)


@t.overload
def get_list_of_strings(
    data: dict[str, t.Any],
    key: str,
    *,
    default: None = None,
) -> list[str] | None: ...


@t.overload
def get_list_of_strings(
    data: dict[str, t.Any],
    key: str,
    *,
    default: _T,
) -> list[str] | _T: ...


def get_list_of_strings(
    data: dict[str, t.Any],
    key: str,
    *,
    default: _T | None = None,
) -> list[str] | _T | None:
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


@dataclasses.dataclass
class Location:
    line: int
    column: int | None = None

    @staticmethod
    def from_json(data: object) -> Location:
        if not isinstance(data, Mapping):
            raise ValueError(f"Expected mapping, got {type(data)}")
        return Location(**data)


Level = t.Literal["error", "warning", "info"]


@dataclasses.dataclass
class Message:
    file: str | None
    start: Location | None
    end: Location | None
    level: Level
    id: str | None
    message: str
    symbol: str | None = None
    hint: str | None = None
    note: str | None = None
    url: str | None = None

    @staticmethod
    def from_json(data: object) -> Message:
        if not isinstance(data, Mapping):
            raise ValueError(f"Expected mapping, got {type(data)}")
        params = {k: v for k, v in data.items()}
        start = params.pop("start", None)
        end = params.pop("end", None)
        if start is not None:
            params["start"] = Location.from_json(start)
        if end is not None:
            params["end"] = Location.from_json(end)
        return Message(**params)


def report_result(messages: list[Message]) -> int:
    has_error = any(message.level in ("warning", "error") for message in messages)
    data = {
        "messages": [dataclasses.asdict(message) for message in messages],
    }
    print(json.dumps(data))
    return 1 if has_error else 0
