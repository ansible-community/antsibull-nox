# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
YAML helper.
"""

from __future__ import annotations

from pathlib import Path


class YAMLField:
    """
    Editor for a YAML value.
    """

    def __init__(
        self,
        *,
        editor: "YAMLEditor",
        line: int,
        prefix: str,
        value: str,
        quote: str = "",
        line_ending: str = "\n",
    ) -> None:
        self._editor = editor
        self._line = line
        self._prefix = prefix
        self._value = value
        self._quote = quote
        self._line_ending = line_ending

    @property
    def value(self) -> str:
        """
        Retrieve the current value.
        """
        return self._value

    def set(self, value: str) -> None:
        """
        Set a new value.
        """
        self._value = value
        # pylint: disable-next=protected-access
        self._editor._lines[self._line] = (
            f"{self._prefix}{self._quote}{self._value}{self._quote}{self._line_ending}"
        )


class YAMLEditor:
    """
    Basic YAML editor.
    """

    def __init__(self, *, path: Path) -> None:
        """
        Read YAML file's contents.
        """
        self._path = path
        with self._path.open("rt", encoding="utf-8") as f:
            self._lines = f.readlines()
        self._start = 0
        self._end = len(self._lines)
        had_content = False
        for index, line in enumerate(self._lines):
            line = line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if line == "---":
                if had_content:
                    self._end = index
                    break
                self._start = index + 1
                had_content = True
            elif line == "...":
                self._end = index
                break
            else:
                had_content = True

    def write(self) -> None:
        """
        Write YAML file back to disk.
        """
        with self._path.open("wt", encoding="utf-8") as f:
            f.writelines(self._lines)

    def find(self, *, key: str) -> YAMLField | None:
        """
        Find (top-level) key in first document.
        """
        prefix = f"{key}:"
        for index in range(self._start, self._end):
            line = self._lines[index]
            if not line.startswith(prefix):
                continue
            remainder = line[len(prefix) :]
            if not remainder.startswith(" "):
                raise ValueError(
                    f"Can only work on simple string-valued YAML keys {key!r}"
                )
            content = remainder.lstrip()
            if content.startswith(("|", ">")):
                raise ValueError(
                    f"Can only work on simple string-valued YAML keys {key!r}"
                )
            prefix_length = len(line) - len(content)
            line_ending = ""
            if content.endswith(("\n\r", "\r\n")):
                line_ending = content[-2:]
                content = content[:-2]
            elif content.endswith(("\n", "\r")):
                line_ending = content[-1:]
                content = content[:-1]
            quote = ""
            if len(content) > 1:
                if content.startswith("'") and content.endswith("'"):
                    quote = "'"
                    content = content[1:-1]
                elif content.startswith('"') and content.endswith('"'):
                    quote = '"'
                    content = content[1:-1]
            return YAMLField(
                editor=self,
                line=index,
                prefix=line[:prefix_length],
                value=content,
                quote=quote,
                line_ending=line_ending,
            )
        return None

    def create(self, *, key: str, value: str) -> YAMLField:
        """
        Add (top-level) key in first document.
        """
        index = self._end
        self._lines.insert(index, "")
        self._end += 1
        return YAMLField(editor=self, line=index, prefix=f"{key}: ", value=value)


__all__ = ("YAMLEditor",)
