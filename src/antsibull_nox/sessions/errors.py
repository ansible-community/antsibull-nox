# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Error reporting.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
from pathlib import Path

import nox

from ..data.antsibull_nox_data_util import Level as _DataLevel
from ..data.antsibull_nox_data_util import Location as _DataLocation
from ..data.antsibull_nox_data_util import Message as _DataMessage


class Level(enum.Enum):
    """
    Message level.
    """

    INFO = 1
    WARNING = 2
    ERROR = 3


@dataclasses.dataclass(frozen=True)
class Location:
    """
    A location in a source file.
    """

    line: int
    column: int | None = None

    def __get_tuple(self) -> tuple[int, bool, int]:
        """Helper for comparison functions."""
        return self.line, self.column is not None, self.column or 0

    def __lt__(self, other: Location) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() < o

    def __le__(self, other: Location) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() <= o

    def __gt__(self, other: Location) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() > o

    def __ge__(self, other: Location) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() >= o


@dataclasses.dataclass(frozen=True)
class Message:
    """
    A linter output message.
    """

    file: str | None
    position: Location | None
    end_position: Location | None
    level: Level
    id: str | None
    message: str
    symbol: str | None = None
    hint: str | None = None
    note: str | None = None
    url: str | None = None

    def __get_tuple(
        self,
    ) -> tuple[
        bool,
        str,
        bool,
        Location | None,
        bool,
        Location | None,
        Level,
        bool,
        str,
        str,
        bool,
        str,
        bool,
        str,
        bool,
        str,
        bool,
        str,
    ]:
        """Helper for comparison functions."""
        return (
            self.file is not None,
            self.file or "",
            self.position is not None,
            self.position,
            self.end_position is not None,
            self.end_position,
            self.level,
            self.id is not None,
            self.id or "",
            self.message,
            self.symbol is not None,
            self.symbol or "",
            self.hint is not None,
            self.hint or "",
            self.note is not None,
            self.note or "",
            self.url is not None,
            self.url or "",
        )

    def __lt__(self, other: Message) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() < o

    def __le__(self, other: Message) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() <= o

    def __gt__(self, other: Message) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() > o

    def __ge__(self, other: Message) -> bool:
        o = other.__get_tuple()  # pylint: disable=protected-access
        return self.__get_tuple() >= o


def print_messages(
    *, session: nox.Session, messages: list[Message], fail_msg: str
) -> None:
    """
    Print messages, and error out if at least one error has been found.
    """
    found_error = False
    for message in sorted(messages):
        loc_line = 0
        loc_column = 0
        if message.position is not None:
            loc_line = message.position.line
            loc_column = message.position.column or 0
        prefix = f"{message.file or ''}:{loc_line}:{loc_column}:"
        if message.id is not None:
            prefix = f"{prefix} [{message.id}]"
        content = message.message
        if message.symbol is not None:
            content = f"{content} [{message.symbol}]"
        if message.hint is not None:
            content = f"{content}\n{message.hint}"
        if message.note is not None:
            content = f"{content}\nNote: {message.note}"
        first = True
        for line in content.splitlines():
            print(f"{prefix} {line}")
            if first:
                first = False
                prefix = " " * len(prefix)
        if message.level in (Level.WARNING, Level.ERROR):
            found_error = True
    if found_error:
        session.error(fail_msg)


def parse_pylint_json2_errors(
    *,
    source_path: Path,
    output: str,
) -> list[Message]:
    """
    Parse errors reported by pylint in 'json2' format.
    """
    try:
        data = json.loads(output)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse pylint output: {exc}\n{output}",
            )
        ]

    messages = []
    if data["messages"]:
        for message in data["messages"]:
            path = os.path.relpath(message["absolutePath"], source_path)
            messages.append(
                Message(
                    file=path,
                    position=Location(line=message["line"], column=message["column"]),
                    end_position=None,
                    level=Level.ERROR,
                    id=message["messageId"],
                    symbol=message["symbol"],
                    message=message["message"],
                )
            )
    return messages


def parse_ruff_check_errors(
    *,
    source_path: Path,
    output: str,
) -> list[Message]:
    """
    Parse errors reported by ruff check in 'json' format.
    """
    try:
        data = json.loads(output)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse ruff check output: {exc}\n{output}",
            )
        ]

    messages = []
    for message in data:
        path = os.path.relpath(message["filename"], source_path)
        hint: str | None = None
        if message.get("fix"):
            fix = message["fix"]
            if "message" in fix:
                hint = fix["message"]
        messages.append(
            Message(
                file=path,
                position=Location(
                    line=message["location"]["row"],
                    column=message["location"]["column"],
                ),
                end_position=Location(
                    line=message["end_location"]["row"],
                    column=message["end_location"]["column"],
                ),
                level=Level.ERROR,
                id=message["code"],
                message=message["message"],
                hint=hint,
                url=message["url"],
            )
        )
    return messages


def parse_mypy_errors(
    *,
    root_path: Path,  # prepared_collections.current_place
    source_path: Path,  # prepared_collections.current_path
    output: str,
) -> list[Message]:
    """
    Process errors reported by mypy in 'json' format.
    """
    messages = []
    _mypy_severity = {
        "error": Level.ERROR,
        "note": Level.INFO,
    }
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            path = os.path.relpath(
                root_path / data["file"],
                source_path,
            )
            level = _mypy_severity.get(data["severity"], Level.ERROR)
            messages.append(
                Message(
                    file=path,
                    position=Location(
                        line=data["line"],
                        column=data["column"],
                    ),
                    end_position=None,
                    level=level,
                    id=data["code"],
                    message=data["message"],
                    hint=data["hint"],
                )
            )
        except Exception:  # pylint: disable=broad-exception-caught
            messages.append(
                Message(
                    file=None,
                    position=None,
                    end_position=None,
                    level=Level.ERROR,
                    id=None,
                    message=f"Cannot parse mypy output: {line}",
                )
            )
    return messages


def parse_bare_framework_errors(
    *,
    output: str,
) -> list[Message]:
    """
    Process errors reported by tools from data with
    antsibull_nox.data.antsibull_nox_data.util.report_result().
    """
    try:
        data = json.loads(output)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse output: {exc}\n{output}",
            )
        ]

    def loc(data: _DataLocation | None) -> Location | None:
        if data is None:
            return None
        return Location(line=data.line, column=data.column)

    levels: dict[_DataLevel, Level] = {
        "error": Level.ERROR,
        "warning": Level.WARNING,
        "info": Level.INFO,
    }

    messages = []
    for message in data["messages"]:
        msg = _DataMessage.from_json(message)
        messages.append(
            Message(
                file=msg.file,
                position=loc(msg.start),
                end_position=loc(msg.end),
                level=levels.get(msg.level, Level.ERROR),
                id=msg.id,
                message=msg.message,
                symbol=msg.id,
                hint=msg.hint,
                note=msg.note,
                url=msg.url,
            )
        )
    return messages


_JSON_END: dict[str, str] = {
    "{": "}",
    "[": "]",
}
_JSON_START: tuple[str, ...] = tuple(_JSON_END.keys())


def _find_json_line(output: str) -> str:
    """
    Given output of a program, find a JSON object or list in a single line.

    This function assumes that the line containing the JSON only contains
    whitespace before and after the JSON.
    """
    for line in output.splitlines():
        line = line.strip()
        if line.startswith(_JSON_START) and line.endswith(_JSON_END[line[0]]):
            return line
    return output


def _find_json(output: str) -> str:
    """
    Given output of a program, find a JSON object or list in it.

    This function assumes that the object starts and ends in a line that does not
    have any noise preceeding / succeeding it.
    """
    lines = output.splitlines()
    for start, line in enumerate(lines):
        line = line.strip()
        if line.startswith(_JSON_START):
            end_char = _JSON_END[line[0]]
            break
    else:
        # Didn't find start
        return output
    lines = lines[start:]
    for end in range(len(lines) - 1, -1, -1):
        if lines[end].strip().endswith(end_char):
            break
    else:
        # Didn't find end
        return output
    lines = lines[: end + 1]
    return "\n".join(lines)


def parse_antsibull_docs_errors(
    *,
    output: str,
) -> list[Message]:
    """
    Parse errors reported by antsibull-docs lint-collection-docs 'json' format.
    """
    try:
        data = json.loads(_find_json(output))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse antsibull-docs lint-collection-docs output: {exc}\n{output}",
            )
        ]

    messages = []
    for message in data["messages"]:
        messages.append(
            Message(
                file=message["path"],
                position=(
                    Location(
                        line=message["row"],
                        column=message.get("column"),
                    )
                    if message.get("row") is not None
                    else None
                ),
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=message["message"],
            )
        )
    return messages
