# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Error reporting.
"""

from __future__ import annotations

import sys
import types
import typing as t

import nox

from ...messages import Level, Message

if t.TYPE_CHECKING:
    Formatter = t.Callable[[list[Message]], t.Generator[str]]


def split_lines_with_prefix(
    text: str, *, prefix: str = "", separator: str = " "
) -> t.Generator[str]:
    """
    Given a text with newlines, emit single lines with optional prefix.

    By default prefix and line are separated by a single space.
    This can be changed by passing an appropriate ``separator``.
    """
    for index, line in enumerate(text.rstrip("\n").splitlines()):
        if index == 1:
            prefix = " " * len(prefix)
        yield f"{prefix}{separator}{line}"


class SynchronizedOutput:
    """
    Print output to stdout, but keep it synchronized to stderr.
    """

    def __init__(self) -> None:
        self._has_output = False

    @property
    def has_output(self) -> bool:
        """
        Whether any output has been emitted.
        """
        return self._has_output

    def msg(self, message: str) -> None:
        """
        Print a one-line message.
        """
        if not self._has_output:
            sys.stderr.flush()
            self._has_output = True
        print(message)

    def __enter__(self) -> t.Self:
        return self

    def __exit__(
        self,
        exc_type: t.Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> t.Literal[False]:
        if self._has_output:
            sys.stdout.flush()
        return False


def should_fail(messages: list[Message]) -> bool:
    """
    Determine whether a test with the given list of output messages should fail.
    """
    return any(message.level in (Level.WARNING, Level.ERROR) for message in messages)


def format_messages_plain(messages: list[Message]) -> t.Generator[str]:
    """
    Format a list of messages as a sequence of lines.
    """
    for message in sorted(messages):
        loc_line = "0"
        loc_column = 0
        if message.position is not None:
            loc_line = str(message.position.line)
            loc_column = message.position.column or 0
            if not message.position.exact:
                loc_line = f"~{loc_line}"
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
        yield from split_lines_with_prefix(content, prefix=prefix)


def get_formatter() -> Formatter:
    """
    Return the suggested message formatter to use.
    """
    return format_messages_plain


def print_messages(
    *, session: nox.Session, messages: list[Message], fail_msg: str
) -> None:
    """
    Print messages, and error out if at least one error has been found.
    """
    with SynchronizedOutput() as output:
        for line in get_formatter()(messages):
            output.msg(line)
    if should_fail(messages):
        session.error(fail_msg)
