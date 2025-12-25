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


__all__ = ("Level", "Location", "Message")
