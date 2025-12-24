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

    file: str
    position: Location
    end_position: Location | None
    level: Level
    id: str | None
    message: str
    symbol: str | None = None
    hint: str | None = None
    url: str | None = None

    def __get_tuple(
        self,
    ) -> tuple[
        str,
        Location,
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
    ]:
        """Helper for comparison functions."""
        return (
            self.file,
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
        prefix = (
            f"{message.file}:{message.position.line}:{message.position.column or 0}: "
        )
        if message.id is not None:
            prefix = f"{prefix} [{message.id}]"
        content = message.message
        if message.symbol is not None:
            content = f"{content} [{message.symbol}]"
        first = True
        for line in content.splitlines():
            print(f"{prefix}{line}")
            if first:
                first = False
                prefix = " " * len(prefix)
        if message.level == Level.ERROR:
            found_error = True
    if found_error:
        session.error(fail_msg)


def process_pylint_json2_errors(
    *,
    session: nox.Session,
    source_path: Path,
    output: str,
    fail_msg: str = "Pylint failed",
) -> None:
    """
    Process errors reported by pylint in 'json2' format.
    """
    try:
        data = json.loads(output)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        session.warn(f"Cannot parse pylint output: {exc}")
        print(output)
        session.error(fail_msg)

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
    print_messages(session=session, messages=messages, fail_msg=fail_msg)


def process_ruff_check_errors(
    *,
    session: nox.Session,
    source_path: Path,
    output: str,
    fail_msg: str = "Ruff failed",
) -> None:
    """
    Process errors reported by ruff check in 'json' format.
    """
    try:
        data = json.loads(output)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        session.warn(f"Cannot parse ruff check output: {exc}")
        print(output)
        session.error(fail_msg)

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
    print_messages(session=session, messages=messages, fail_msg=fail_msg)
