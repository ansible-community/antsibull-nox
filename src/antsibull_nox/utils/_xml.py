# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Basic XML serialization.
"""

from __future__ import annotations

import re
import typing as t

if t.TYPE_CHECKING:
    _T = t.TypeVar("_T")


_VALID_NAME = re.compile(
    r"""^[^!"#$%&'()*+,/;<=>?@[\\\]^`{|}~,. 0-9-][^!"#$%&'()*+,/;<=>?@[\\\]^`{|}~, ]*$"""
)


_ESCAPE_STRINGS: dict[str, str] = {
    "'": "&apos;",
    '"': "&quot;",
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
}


def _valid_char(ch: str) -> bool:
    value = ord(ch)
    return not (value == 0 or 0xD7FF < value < 0xE000 or 0xFFFD < value < 0x10000)


def _needs_to_escape(ch: str) -> bool:
    value = ord(ch)
    return (
        value <= 8
        or 0x0B <= value <= 0x1F
        or 0xD7FF < value < 0xE000
        or 0xFFFD < value < 0x10000
    )


def _escape_value(value: str, *, accept: str = "") -> str:
    result = []
    for ch in value:
        if (rep := _ESCAPE_STRINGS.get(ch)) is not None:
            result.append(rep)
        elif _needs_to_escape(ch) and ch not in accept:
            v = hex(ord(ch))[2:]
            result.append(f"&#x{v};")
        else:
            result.append(ch)
    return "".join(result)


class _LineBreak:
    pass


_LINE_BREAK = _LineBreak()


def _ends_with_line_break(result: list[str | _LineBreak]) -> bool:
    return bool(result) and result[-1] is _LINE_BREAK


class Node:
    """
    Represent a regular node in XML.
    """

    def __init__(
        self, tag: str, *, attributes: dict[str, str | None] | None = None
    ) -> None:
        """
        Create a new node with tag ``tag`` and attributes ``attributes``.
        """
        if not _VALID_NAME.match(tag):
            raise ValueError(f"Invalid tag {tag!r}")
        self.tag = tag
        self.attributes: dict[str, str | None] = {}
        if attributes:
            for attribute, value in attributes.items():
                if not _VALID_NAME.match(attribute):
                    raise ValueError(f"Invalid attribute name {attribute!r}")
                self.attributes[attribute] = value
        self.children: list[Node | Text] = []

    def append_node(
        self, tag: str, *, attributes: dict[str, str | None] | None = None
    ) -> Node:
        """
        Create and append a new node with tag ``tag`` and attributes ``attributes`` to this node.
        Return the new node.
        """
        node = Node(tag, attributes=attributes)
        self.append(node)
        return node

    def set(self, attribute: str, value: str | None) -> t.Self:
        """
        For this node, set the given attribute to the given value.
        """
        if not _VALID_NAME.match(attribute):
            raise ValueError(f"Invalid attribute name {attribute!r}")
        self.attributes[attribute] = value
        return self

    def delete(self, attribute: str) -> t.Self:
        """
        For this node, delete the given attribute.
        """
        self.attributes.pop(attribute, None)
        return self

    @t.overload
    def get(self, attribute: str, default: None = None) -> str | None: ...

    @t.overload
    def get(self, attribute: str, default: _T) -> str | _T: ...

    def get(self, attribute: str, default: _T | None = None) -> str | _T | None:
        """
        Return the value of the given attribute for this node.
        If the attribute hasn't been set, the default value ``default`` is returned.
        """
        return self.attributes.get(attribute, default)

    def append(self, child: Node | Text) -> t.Self:
        """
        Append the given node to the current node.
        """
        self.children.append(child)
        return self

    def _serialize(
        self, result: list[str | _LineBreak], indent: str, add_indent: str
    ) -> None:
        if _ends_with_line_break(result):
            result.append(indent)
        parts = [self.tag]
        for key, value in self.attributes.items():
            if value is not None:
                parts.append(f'{key}="{_escape_value(value)}"')
            else:
                parts.append(key)
        parts_str = " ".join(parts)
        if self.children:
            result.append(f"<{parts_str}>")
            result.append(_LINE_BREAK)
            new_indent = indent + add_indent
            for child in self.children:
                # pylint: disable-next=protected-access
                child._serialize(result, new_indent, add_indent)
            if _ends_with_line_break(result):
                result.append(indent)
            result.append(f"</{self.tag}>")
            result.append(_LINE_BREAK)
        else:
            result.append(f"<{parts_str}/>")
            result.append(_LINE_BREAK)

    def serialize(
        self, *, pretty_print: bool = False, add_header: bool = True, indent: str = "\t"
    ) -> str:
        """
        Serialize the node as an XML document or fragment (``add_header == False``).
        """
        result: list[str | _LineBreak] = []
        if add_header:
            result.append('<?xml version="1.1" encoding="utf-8"?>\n')
        self._serialize(result, "", indent if pretty_print else "")
        str_result: list[str]
        if not pretty_print:
            str_result = [part for part in result if part is not _LINE_BREAK]  # type: ignore
        else:
            str_result = ["\n" if part is _LINE_BREAK else part for part in result]  # type: ignore
            if str_result:
                str_result.append("\n")
        return "".join(str_result)


class Text:
    """
    Represent a text node in XML.
    """

    def __init__(self, content: str) -> None:
        """
        Create a new text node with given content.
        """
        self.content = content

    def _serialize(
        self,
        result: list[str | _LineBreak],
        indent: str,  # pylint: disable=unused-argument
        add_indent: str,  # pylint: disable=unused-argument
    ) -> None:
        if _ends_with_line_break(result):
            del result[-1]
        result.append(_escape_value(self.content, accept="\n"))


__all__ = (
    "Node",
    "Text",
)
