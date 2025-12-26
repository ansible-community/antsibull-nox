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
import functools
import os
import sys
import types
import typing as t

import nox

from ...messages import Level, Location, Message
from . import IN_CI, nox_has_color

if t.TYPE_CHECKING:
    Formatter = t.Callable[[list[Message]], t.Generator[str]]


OutputFormat = t.Literal["plain", "fancy"]


@dataclasses.dataclass(frozen=True, eq=False, repr=False)
class Markings:
    """
    Collection of marking symbols.
    """

    line_indicator: str
    pos_indicator: str
    underline_indicator: str
    box_left_top: str
    box_left: str
    box_left_bottom: str
    box_bottom: str
    box_right_bottom: str
    box_right: str
    box_right_top: str
    box_top: str
    horizontal_ellipsis: str
    vertical_ellipsis: str


ASCII_MARKINGS = Markings(
    line_indicator=">",
    pos_indicator="^",
    underline_indicator="^",
    box_left_top="/",
    box_left="|",
    box_left_bottom="\\",
    box_bottom="-",
    box_right_bottom="/",
    box_right="|",
    box_right_top="\\",
    box_top="-",
    horizontal_ellipsis="...",
    vertical_ellipsis=":",
)

UNICODE_MARKINGS = Markings(
    # https://en.wikipedia.org/wiki/Arrows_%28Unicode_block%29
    line_indicator="→",
    pos_indicator="↑",
    underline_indicator="▔",
    # https://en.wikipedia.org/wiki/Box-drawing_characters
    box_left_top="┌",
    box_left="│",
    box_left_bottom="└",
    box_bottom="─",
    box_right_bottom="┘",
    box_right="│",
    box_right_top="┐",
    box_top="─",
    horizontal_ellipsis="…",
    vertical_ellipsis="⋮",
)


@functools.cache
def get_box_markings() -> Markings:
    """
    Determine how to draw boxes.
    """
    if os.getenv("ANTSIBULL_BOX_MARKINGS") == "ascii":
        return ASCII_MARKINGS
    return UNICODE_MARKINGS


@functools.cache
def get_output_format() -> OutputFormat:
    """
    Determine the output format.
    """
    output_format = os.getenv("ANTSIBULL_OUTPUT_FORMAT")
    if output_format in t.get_args(OutputFormat):
        return t.cast(OutputFormat, output_format)
    if IN_CI:
        return "plain"
    return "fancy"


def split_lines(text: str) -> list[str]:
    """
    Given a text with newlines, split it up into single lines.
    """
    return text.rstrip("\n").splitlines()


def split_lines_with_prefix(
    text: str, *, prefix: str = "", separator: str = " "
) -> t.Generator[str]:
    """
    Given a text with newlines, emit single lines with optional prefix.

    By default prefix and line are separated by a single space.
    This can be changed by passing an appropriate ``separator``.
    """
    for index, line in enumerate(split_lines(text)):
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


_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_FAINT = "\x1b[2m"
_ITALICS = "\x1b[3m"
_UNDERLINE = "\x1b[4m"


class Color(enum.StrEnum):
    """
    ANSI colors.
    """

    NONE = ""
    BLACK = "\x1b[30m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    WHITE = "\x1b[37m"
    BRIGHT_BLACK = "\x1b[90m"
    BRIGHT_RED = "\x1b[91m"
    BRIGHT_GREEN = "\x1b[92m"
    BRIGHT_YELLOW = "\x1b[93m"
    BRIGHT_BLUE = "\x1b[94m"
    BRIGHT_MAGENTA = "\x1b[95m"
    BRIGHT_CYAN = "\x1b[96m"
    BRIGHT_WHITE = "\x1b[97m"


@dataclasses.dataclass(frozen=True)
class _Formatting:
    color: Color = Color.NONE
    bold: bool = False
    faint: bool = False
    italics: bool = False
    underline: bool = False

    def update(
        self,
        *,
        color: Color | None = None,
        bold: bool | None = None,
        faint: bool | None = None,
        italics: bool | None = None,
        underline: bool | None = None,
    ) -> _Formatting:
        """
        Update attributes.
        """
        if bold and faint:
            raise ValueError("Text cannot be both bold and faint")
        new_bold = self.bold
        new_faint = self.faint
        if bold is not None:
            new_bold = bold
            if new_bold:
                new_faint = False
        if faint is not None:
            new_faint = faint
            if new_faint:
                new_bold = False
        return _Formatting(
            self.color if color is None else color,
            new_bold,
            new_faint,
            self.italics if italics is None else italics,
            self.underline if underline is None else underline,
        )

    def eq_color(self, other: _Formatting) -> bool:
        """Compare color attributes of two formattings."""
        return self.color == other.color

    def eq_formatting(self, other: _Formatting) -> bool:
        """Compare formatting attributes of two formattings."""
        return (
            self.bold == other.bold
            and self.faint == other.faint
            and self.italics == other.italics
            and self.underline == other.underline
        )

    def _new_format(
        self,
        *,
        use_color: bool,
        use_formatting: bool,
    ) -> list[str]:
        result = []
        if use_formatting:
            if self.bold:
                result.append(_BOLD)
            if self.faint:
                result.append(_FAINT)
            if self.italics:
                result.append(_ITALICS)
            if self.underline:
                result.append(_UNDERLINE)
        if use_color and self.color is not Color.NONE:
            result.append(self.color)
        return result

    def _update_format(
        self,
        *,
        use_color: bool,
        use_formatting: bool,
        previous: _Formatting,
    ) -> list[str]:
        # Determine whether need a reset
        needs_reset = False
        if use_formatting and not needs_reset:
            needs_reset = (
                (not self.bold and previous.bold)
                or (not self.faint and previous.faint)
                or (not self.italics and previous.italics)
                or (not self.underline and previous.underline)
            )
        if use_color and not needs_reset:
            needs_reset = self.color != previous.color and self.color is Color.NONE

        # Compose codes
        result = []
        if needs_reset:
            result.append(_RESET)
        if use_formatting:
            if self.bold and (needs_reset or self.bold != previous.bold):
                result.append(_BOLD)
            if self.faint and (needs_reset or self.faint != previous.faint):
                result.append(_FAINT)
            if self.italics and (needs_reset or self.italics != previous.italics):
                result.append(_ITALICS)
            if self.underline and (needs_reset or self.underline != previous.underline):
                result.append(_UNDERLINE)
        if (
            use_color
            and self.color is not Color.NONE
            and (needs_reset or self.color != previous.color)
        ):
            result.append(self.color)
        return result

    def format(
        self,
        *,
        use_color: bool,
        use_formatting: bool,
        previous: _Formatting | None = None,
    ) -> list[str]:
        """
        Compute format update as sequence of ANSI codes.
        """
        if previous is None:
            return self._new_format(use_color=use_color, use_formatting=use_formatting)
        return self._update_format(
            use_color=use_color, use_formatting=use_formatting, previous=previous
        )


_CLEAR = _Formatting()


class ColorComposer:
    """
    Compose text that uses optional colors and formatting.
    """

    def __init__(self, *, use_color: bool, use_formatting: bool) -> None:
        """
        Set up color and formatting composer.
        """
        self.use_color = use_color
        self.use_formatting = use_formatting
        self.last_formatting = _CLEAR
        self.formatting = _CLEAR
        self.output: list[str] = []

    def format(
        self,
        *,
        color: Color | None = None,
        bold: bool | None = None,
        faint: bool | None = None,
        italics: bool | None = None,
        underline: bool | None = None,
    ) -> t.Self:
        """
        Adjust formatting.
        """
        self.formatting = self.formatting.update(
            color=color, bold=bold, faint=faint, italics=italics, underline=underline
        )
        return self

    def add_text(
        self,
        text: str,
        *,
        color: Color | None = None,
        bold: bool | None = None,
        faint: bool | None = None,
        italics: bool | None = None,
        underline: bool | None = None,
    ) -> t.Self:
        """
        Add text with optional formatting adjustment.
        """
        self.format(
            color=color, bold=bold, faint=faint, italics=italics, underline=underline
        )
        if text:
            self.output.extend(
                self.formatting.format(
                    use_color=self.use_color,
                    use_formatting=self.use_formatting,
                    previous=self.last_formatting,
                )
            )
            self.last_formatting = self.formatting
            self.output.append(text)
        return self

    @property
    def empty(self) -> bool:
        """
        Whether the formatter already has output.
        """
        return not self.output

    @property
    def value(self) -> str:
        """
        Obtain formatted value.
        """
        result = "".join(self.output)
        if (self.use_color and not self.last_formatting.eq_color(_CLEAR)) or (
            self.use_formatting and not self.last_formatting.eq_formatting(_CLEAR)
        ):
            result = f"{result}{_RESET}"
        return result


class _ContentProvider:
    def __init__(self) -> None:
        self.filename: str | None = None
        self.content: list[str] | None = None

    def _ensure_loaded(self, filename: str) -> None:
        if self.filename == filename:
            return
        self.filename = filename
        self.content = None
        try:
            with open(filename, "rt", encoding="utf-8") as f:
                self.content = f.read().splitlines()
        except Exception:  # pylint: disable=broad-exception-caught
            # This can be caused by I/O errors, decoding errors, out of memory errors, ...
            # In all these cases, simply do not show the content.
            pass

    @staticmethod
    def _expand(line: str, *, tabulator_width: int = 8) -> str:
        result = []
        idx = 0
        for idx, part in enumerate(line.split("\t")):
            if idx:
                act_tab_w = tabulator_width - (idx % tabulator_width)
                if act_tab_w == 0:
                    act_tab_w = tabulator_width
                result.append(" " * act_tab_w)
                idx += act_tab_w
            result.append(part)
            idx += len(part)
        return "".join(result)

    @staticmethod
    def _get_column(
        line: str, column: int | None, *, tabulator_width: int = 8, is_end: bool = False
    ) -> int | None:
        if column is None:
            return None
        column -= 1
        idx = 0
        for idx, part in enumerate(line.split("\t")):
            if idx:
                act_tab_w = tabulator_width - (idx % tabulator_width)
                if act_tab_w == 0:
                    act_tab_w = tabulator_width
                if column == 0:
                    return ((idx + act_tab_w - 1) if is_end else idx) + 1
                idx += act_tab_w
                column -= 1
            part_len = len(part)
            if column < part_len:
                return idx + column + 1
            idx += part_len
            column -= part_len
        return idx + column + 1

    @staticmethod
    def _find(index: int, direction: int, content: list[str]) -> int:
        length = len(content)
        candidate = index
        for _ in range(2):
            candidate += direction
            if candidate < 0 or candidate >= length:
                break
            if content[candidate].strip():
                return candidate
        candidate = index + direction
        if candidate < 0 or candidate >= length:
            return index
        return candidate

    def get_content_lines(
        self, *, filename: str, start: Location, end: Location | None
    ) -> (
        tuple[
            list[tuple[int | None, str]],
            tuple[int, int | None],
            tuple[int, int | None] | None,
        ]
        | None
    ):
        """
        Return lines containing the start and end locations.
        """
        self._ensure_loaded(filename)
        if self.content is None:
            return None
        last_idx = first_idx = start.line - 1
        if end is not None:
            first_idx = min(first_idx, end.line - 1)
            last_idx = max(last_idx, end.line - 1)
        act_first_idx = first_idx
        act_last_idx = last_idx
        first_idx = self._find(first_idx, -1, self.content)
        last_idx = self._find(last_idx, +1, self.content)
        result: list[tuple[int | None, str]] = []
        if first_idx > 0:
            result.append((None, ""))
        if act_last_idx - act_first_idx > 5:
            for idx in range(first_idx, act_first_idx + 2):
                result.append((idx + 1, self._expand(self.content[idx])))
            result.append((None, ""))
            for idx in range(act_last_idx - 1, last_idx + 1):
                result.append((idx + 1, self._expand(self.content[idx])))
        else:
            for idx in range(first_idx, last_idx + 1):
                result.append((idx + 1, self._expand(self.content[idx])))
        if last_idx + 1 < len(self.content):
            result.append((None, ""))
        return (
            result,
            (start.line, self._get_column(self.content[start.line], start.column)),
            (
                None
                if end is None
                else (end.line, self._get_column(self.content[end.line], end.column))
            ),
        )


def _determine_marker(
    inside: bool,
    line_no: int | None,
    content_start: tuple[int, int | None],
    content_end: tuple[int, int | None] | None,
    extra_indent: str,
    markings: Markings,
) -> tuple[bool, bool, str, str, str]:
    last_inside = False
    before_mark = ""
    after_mark = ""
    this_extra_indent = extra_indent
    if line_no == content_start[0]:
        inside = True
        if content_end is None:
            last_inside = True
            if content_start[1] is None:
                this_extra_indent = f"{markings.line_indicator} "
            else:
                after_mark = (
                    extra_indent + " " * (content_start[1] - 1) + markings.pos_indicator
                )
        elif content_end[0] == content_start[0]:
            last_inside = True
            if content_start[1] is not None and content_end[1] is not None:
                after_mark = (
                    extra_indent
                    + " " * (content_start[1] - 1)
                    + markings.underline_indicator * (content_end[1] - content_start[1])
                )
            else:
                before_mark = markings.box_left_top
                this_extra_indent = f"{markings.box_left} "
                after_mark = markings.box_left_bottom
        else:
            before_mark = markings.box_left_top
            this_extra_indent = f"{markings.box_left} "
    elif content_end is not None and line_no == content_end[0]:
        last_inside = True
        this_extra_indent = f"{markings.box_left} "
        after_mark = markings.box_left_bottom
        if content_end[1] is not None:
            after_mark += (
                markings.box_bottom * content_end[1] + markings.box_right_bottom
            )
    elif inside:
        this_extra_indent = f"{markings.box_left} "
    return inside, last_inside, before_mark, after_mark, this_extra_indent


def _render_code(
    content: list[tuple[int | None, str]],
    content_start: tuple[int, int | None],
    content_end: tuple[int, int | None] | None,
    mkcomp: t.Callable[[], ColorComposer],
    markings: Markings,
) -> t.Generator[str]:
    line_prefixes = [
        markings.vertical_ellipsis if line_no is None else str(line_no)
        for line_no, _ in content
    ]
    max_prefix_len = max(len(prefix) for prefix in line_prefixes)
    empty = " " * max_prefix_len
    line_prefixes = [
        " " * (max_prefix_len - len(prefix)) + prefix for prefix in line_prefixes
    ]
    extra_indent = ""
    if content_end is not None or content_start[1] is None:
        extra_indent = "  "
    inside = False
    for prefix, (line_no, line) in zip(line_prefixes, content):
        comp = mkcomp()
        comp.add_text(prefix, faint=True)
        comp.add_text(f" {markings.box_left} ", faint=True)
        inside, last_inside, before_mark, after_mark, this_extra_indent = (
            _determine_marker(
                inside, line_no, content_start, content_end, extra_indent, markings
            )
        )
        comp.add_text(
            this_extra_indent,
            color=None if this_extra_indent is extra_indent else Color.RED,
            faint=False,
        )
        comp.add_text(line, color=Color.NONE)
        if before_mark:
            before_comp = mkcomp()
            before_comp.add_text(empty, faint=True)
            before_comp.add_text(f" {markings.box_left} ", faint=True)
            before_comp.add_text(before_mark, faint=False, color=Color.RED)
            yield before_comp.value
        yield comp.value
        if last_inside:
            inside = False
        if after_mark:
            after_comp = mkcomp()
            after_comp.add_text(empty, faint=True)
            after_comp.add_text(f" {markings.box_left} ", faint=True)
            after_comp.add_text(after_mark, faint=False, color=Color.RED)
            yield after_comp.value


def _compose_first_line(
    message: Message, mkcomp: t.Callable[[], ColorComposer]
) -> ColorComposer:
    comp = mkcomp()
    if message.file:
        comp.add_text(message.file or "")
        if message.position is not None:
            comp.add_text(
                f":{'' if message.position.exact else '~'}{message.position.line}"
            )
            if message.position.column is not None:
                comp.add_text(f":{message.position.column}")
        comp.add_text(":")
    if message.id is not None:
        if not comp.empty:
            comp.add_text(" ")
        comp.add_text(f"[{message.id}]", color=Color.RED)
    return comp


def format_messages_with_context(
    messages: list[Message], *, color: bool, markings: Markings
) -> t.Generator[str]:
    """
    Format a list of messages as a sequence of lines with context and optional color.
    """

    def mkcomp() -> ColorComposer:
        return ColorComposer(use_color=color, use_formatting=color)

    content_provider = _ContentProvider()
    for index, message in enumerate(sorted(messages)):
        if index:
            yield ""

        # First line: file, start position, ID
        comp = _compose_first_line(message, mkcomp)
        has_first_line = not comp.empty
        if has_first_line:
            yield comp.value

        content: list[tuple[int | None, str]] | None = None
        content_start: tuple[int, int | None] = (0, None)
        content_end: tuple[int, int | None] | None = None
        if message.file and message.position and message.position.exact:
            content_tuple = content_provider.get_content_lines(
                filename=message.file,
                start=message.position,
                end=(
                    message.end_position
                    if message.end_position and message.end_position.exact
                    else None
                ),
            )
            if content_tuple is not None:
                content, content_start, content_end = content_tuple

        # Afterwards: message with note, and hint if content isn't shown
        msg_content = message.message
        if message.symbol is not None:
            msg_content = f"{msg_content} [{message.symbol}]"
        if message.hint is not None and content is None:
            msg_content = f"{msg_content}\n{message.hint}"
        indent = "  " if has_first_line else ""
        for line in split_lines(msg_content):
            comp = mkcomp()
            comp.add_text(indent)
            comp.add_text(line, bold=True)
            yield comp.value
        if message.note is not None:
            for index, line in enumerate(split_lines(message.note)):
                comp = mkcomp()
                comp.add_text(indent)
                if index == 0:
                    comp.add_text("Note: ", italics=True)
                comp.add_text(line, italics=False)
                yield comp.value

        if content is not None:
            yield from _render_code(
                content, content_start, content_end, mkcomp, markings
            )

            if message.hint is not None:
                for line in split_lines(message.hint):
                    comp = mkcomp()
                    comp.add_text(indent)
                    comp.add_text(line, color=Color.GREEN, bold=True)
                    yield comp.value


def get_formatter(
    session: nox.Session,
    *,
    output_format: OutputFormat | None = None,
    use_color: bool | None = None,
    markings: Markings | None = None,
) -> Formatter:
    """
    Return the suggested message formatter to use.
    """
    if output_format is None:
        output_format = get_output_format()
    if output_format == "plain":
        return format_messages_plain
    if output_format == "fancy":
        if markings is None:
            markings = get_box_markings()
        return lambda messages: format_messages_with_context(
            messages,
            color=nox_has_color(session) if use_color is None else use_color,
            markings=markings,
        )
    raise AssertionError(f"Invalid output format {output_format}")


def print_messages(
    *, session: nox.Session, messages: list[Message], fail_msg: str
) -> None:
    """
    Print messages, and error out if at least one error has been found.
    """
    with SynchronizedOutput() as output:
        for line in get_formatter(session)(messages):
            output.msg(line)
    if should_fail(messages):
        session.error(fail_msg)


__all__ = (
    "Markings",
    "ASCII_MARKINGS",
    "UNICODE_MARKINGS",
    "get_box_markings",
    "get_output_format",
    "split_lines_with_prefix",
    "SynchronizedOutput",
    "should_fail",
    "format_messages_plain",
    "format_messages_with_context",
    "get_formatter",
    "print_messages",
)
