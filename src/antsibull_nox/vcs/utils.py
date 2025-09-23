# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utilities.
"""

from __future__ import annotations

import fnmatch
import re
import typing as t

_NUMBER = re.compile("([0-9]+)")


class SortableBranchName:
    """
    A branch name that can be compared lexicographically,
    with special handling for integers.
    """

    def __init__(self, branch_name: str) -> None:
        self.branch_name = branch_name
        self.parts: list[
            tuple[t.Literal["i"], int, str] | tuple[t.Literal["l"], str]
        ] = []
        for index, part in enumerate(_NUMBER.split(branch_name)):
            if index % 2 == 1:
                self.parts.append(("i", int(part), part))
            else:
                for letter in part:
                    self.parts.append(("l", letter))

    def __repr__(self) -> str:
        parts = ",".join(repr(p[-1]) for p in self.parts)
        return f"SortableBranchName({self.branch_name!r}, parts={parts})"

    def __str__(self) -> str:
        return self.branch_name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SortableBranchName):
            return False
        return self.branch_name == other.branch_name

    def __lt__(self, other: SortableBranchName) -> bool:
        for a, b in zip(self.parts, other.parts):
            if a[0] == b[0]:
                if a[-1] != b[-1]:
                    # a[1] and b[1] are of the same type, but mypy doesn't notice...
                    return a[1] < b[1]  # type: ignore
            elif a[0] == "l":  # and b[0] == "i"
                # a[1] is a string, but mypy doesn't notice...
                return a[1] < "0"  # type: ignore
            else:  # a[0] == "i" and b[0] == "l"
                # b[1] is a string, but mypy doesn't notice...
                return "9" < b[1]  # type: ignore
        return len(self.parts) < len(other.parts)


def matches(branch: str, branch_list: list[str]) -> bool:
    """
    Test whether the given branch name matches one of the given patterns.
    """
    return any(
        fnmatch.fnmatch(branch, branch_pattern) for branch_pattern in branch_list
    )
