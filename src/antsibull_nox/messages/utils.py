# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Error reporting.
"""

from __future__ import annotations

_JSON_END: dict[str, str] = {
    "{": "}",
    "[": "]",
}
_JSON_START: tuple[str, ...] = tuple(_JSON_END.keys())


def find_json_line(output: str) -> str:
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


def find_json(output: str) -> str:
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


__all__ = ("find_json_line", "find_json")
