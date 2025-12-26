# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

import typing as t

import pytest

from antsibull_nox.messages import (
    Level,
    Location,
    Message,
)
from antsibull_nox.sessions.utils.output import (
    _BOLD,
    _FAINT,
    _ITALICS,
    _RESET,
    _UNDERLINE,
    ASCII_MARKINGS,
    Color,
    ColorComposer,
    Markings,
    _compose_first_line,
    _compose_message_with_note,
    _determine_marker,
    _Formatting,
    _render_code,
    format_messages_plain,
    should_fail,
    split_lines,
    split_lines_with_prefix,
)

SPLIT_LINES_DATA: list[tuple[str, list[str]]] = [
    (
        "",
        [],
    ),
    (
        "\n\n",
        [],
    ),
    (
        "Foo",
        ["Foo"],
    ),
    (
        "Foo\n",
        ["Foo"],
    ),
    (
        "\nFoo",
        ["", "Foo"],
    ),
    (
        "Foo\r\nBar",
        ["Foo", "Bar"],
    ),
    (
        "Foo\rBar",
        ["Foo", "Bar"],
    ),
    (
        "Foo\n\rBar",
        ["Foo", "", "Bar"],
    ),
]


@pytest.mark.parametrize(
    "text, expected_result",
    SPLIT_LINES_DATA,
)
def test_split_lines(text: str, expected_result: list[str]) -> None:
    assert split_lines(text) == expected_result


SPLIT_LINES_WITH_PREFIX_DATA: list[tuple[str, dict[str, t.Any], list[str]]] = [
    (
        "",
        {},
        [],
    ),
    (
        "\n\n",
        {},
        [],
    ),
    (
        "",
        {"at_least_one_line": True},
        [""],
    ),
    (
        "\n\n",
        {"at_least_one_line": True},
        [""],
    ),
    (
        "Foo",
        {},
        [" Foo"],
    ),
    (
        "Foo",
        {"separator": ""},
        ["Foo"],
    ),
    (
        "Foo\nBar",
        {"prefix": "A", "separator": "B"},
        ["ABFoo", " BBar"],
    ),
    (
        "Foo\nBar\n\nBaz\n\n\n",
        {"prefix": "Abc"},
        ["Abc Foo", "    Bar", "    ", "    Baz"],
    ),
]


@pytest.mark.parametrize(
    "text, kwargs, expected_result",
    SPLIT_LINES_WITH_PREFIX_DATA,
)
def test_split_lines_with_prefix(
    text: str, kwargs: dict[str, t.Any], expected_result: list[str]
) -> None:
    assert list(split_lines_with_prefix(text, **kwargs)) == expected_result


SHOULD_FAIL_DATA: list[tuple[list[Message], bool]] = [
    ([], False),
    (
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
        ],
        False,
    ),
    (
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.WARNING,
                id=None,
                message="",
            ),
        ],
        True,
    ),
    (
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="",
            ),
        ],
        True,
    ),
    (
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
        ],
        False,
    ),
    (
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.WARNING,
                id=None,
                message="",
            ),
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
        ],
        True,
    ),
    (
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="",
            ),
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
            ),
        ],
        True,
    ),
]


@pytest.mark.parametrize(
    "messages, expected_result",
    SHOULD_FAIL_DATA,
)
def test_should_fail(messages: list[Message], expected_result: bool) -> None:
    assert should_fail(messages) == expected_result


FORMAT_MESSAGES_PLAIN_DATA: list[tuple[list[Message], list[str]]] = [
    ([], []),
    (
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        [":0:0:"],
    ),
    (
        [
            Message(
                file="foo",
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:0:0:"],
    ),
    (
        [
            Message(
                file=None,
                position=Location(line=5),
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        [":5:0:"],
    ),
    (
        [
            Message(
                file="foo",
                position=Location(line=5),
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:5:0:"],
    ),
    (
        [
            Message(
                file="foo",
                position=Location(line=5, column=10),
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:5:10:"],
    ),
    (
        [
            Message(
                file="foo",
                position=Location(line=5, exact=False),
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:~5:0:"],
    ),
    (
        [
            Message(
                file="foo",
                position=Location(line=5, column=10, exact=False),
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:~5:10:"],
    ),
    (
        [
            Message(
                file="foo",
                position=None,
                end_position=None,
                level=Level.INFO,
                id="bar",
                message="",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:0:0: [bar]"],
    ),
    (
        [
            Message(
                file="foo",
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="bar",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:0:0: bar"],
    ),
    (
        [
            Message(
                file="foo",
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol="bar",
                hint=None,
                note=None,
                url=None,
            ),
        ],
        ["foo:0:0:  [bar]"],
    ),
    (
        [
            Message(
                file="foo",
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint="bar",
                note=None,
                url=None,
            ),
        ],
        ["foo:0:0: ", "         bar"],
    ),
    (
        [
            Message(
                file="foo",
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note="bar",
                url=None,
            ),
        ],
        ["foo:0:0: ", "         Note: bar"],
    ),
    (
        [
            Message(
                file="foo",
                position=None,
                end_position=None,
                level=Level.INFO,
                id=None,
                message="",
                symbol=None,
                hint=None,
                note=None,
                url="bar",
            ),
        ],
        ["foo:0:0:"],
    ),
    (
        [
            Message(
                file="foo",
                position=Location(line=1, column=2),
                end_position=Location(line=3, column=4),
                level=Level.ERROR,
                id="foo",
                message="bar",
                symbol="baz",
                hint="bam",
                note="boom",
                url="fubar",
            ),
        ],
        ["foo:1:2: [foo] bar [baz]", "               bam", "               Note: boom"],
    ),
]


@pytest.mark.parametrize(
    "messages, expected_result",
    FORMAT_MESSAGES_PLAIN_DATA,
)
def test_format_messages_plain(
    messages: list[Message], expected_result: list[str]
) -> None:
    assert list(format_messages_plain(messages)) == expected_result


def test_formatting() -> None:
    assert not _Formatting(color=Color.RED).eq_color(_Formatting(color=Color.GREEN))
    assert _Formatting(bold=True).eq_color(_Formatting(bold=False))
    assert _Formatting(faint=True).eq_color(_Formatting(faint=False))
    assert _Formatting(italics=True).eq_color(_Formatting(italics=False))
    assert _Formatting(underline=True).eq_color(_Formatting(underline=False))

    assert _Formatting(color=Color.RED).eq_formatting(_Formatting(color=Color.GREEN))
    assert not _Formatting(bold=True).eq_formatting(_Formatting(bold=False))
    assert not _Formatting(faint=True).eq_formatting(_Formatting(faint=False))
    assert not _Formatting(italics=True).eq_formatting(_Formatting(italics=False))
    assert not _Formatting(underline=True).eq_formatting(_Formatting(underline=False))

    assert _Formatting().update(color=Color.RED) == _Formatting(color=Color.RED)
    assert _Formatting().update(bold=True) == _Formatting(bold=True)
    assert _Formatting().update(faint=True) == _Formatting(faint=True)
    assert _Formatting(faint=True).update(bold=True) == _Formatting(bold=True)
    assert _Formatting(bold=True).update(faint=True) == _Formatting(faint=True)
    assert _Formatting().update(italics=True) == _Formatting(italics=True)
    assert _Formatting().update(underline=True) == _Formatting(underline=True)

    with pytest.raises(ValueError):
        _Formatting().update(bold=True, faint=True)

    assert _Formatting(color=Color.RED).format(use_color=True, use_formatting=True) == [
        Color.RED.value
    ]
    assert _Formatting(bold=True).format(use_color=True, use_formatting=True) == [_BOLD]
    assert _Formatting(faint=True).format(use_color=True, use_formatting=True) == [
        _FAINT
    ]
    assert _Formatting(italics=True).format(use_color=True, use_formatting=True) == [
        _ITALICS
    ]
    assert _Formatting(underline=True).format(use_color=True, use_formatting=True) == [
        _UNDERLINE
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=True, underline=True
    ).format(use_color=True, use_formatting=True) == [
        _BOLD,
        _FAINT,
        _ITALICS,
        _UNDERLINE,
        Color.RED.value,
    ]

    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=True, underline=True
    ).format(
        use_color=True, use_formatting=True, previous=_Formatting(color=Color.RED)
    ) == [
        _BOLD,
        _FAINT,
        _ITALICS,
        _UNDERLINE,
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=True, underline=True
    ).format(use_color=True, use_formatting=True, previous=_Formatting(bold=True)) == [
        _FAINT,
        _ITALICS,
        _UNDERLINE,
        Color.RED.value,
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=True, underline=True
    ).format(use_color=True, use_formatting=True, previous=_Formatting(faint=True)) == [
        _BOLD,
        _ITALICS,
        _UNDERLINE,
        Color.RED.value,
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=True, underline=True
    ).format(
        use_color=True, use_formatting=True, previous=_Formatting(italics=True)
    ) == [
        _BOLD,
        _FAINT,
        _UNDERLINE,
        Color.RED.value,
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=True, underline=True
    ).format(
        use_color=True, use_formatting=True, previous=_Formatting(underline=True)
    ) == [
        _BOLD,
        _FAINT,
        _ITALICS,
        Color.RED.value,
    ]

    assert _Formatting(
        color=Color.NONE, bold=True, faint=True, italics=True, underline=True
    ).format(
        use_color=True, use_formatting=True, previous=_Formatting(color=Color.RED)
    ) == [
        _RESET,
        _BOLD,
        _FAINT,
        _ITALICS,
        _UNDERLINE,
    ]
    assert _Formatting(
        color=Color.RED, bold=False, faint=True, italics=True, underline=True
    ).format(use_color=True, use_formatting=True, previous=_Formatting(bold=True)) == [
        _RESET,
        _FAINT,
        _ITALICS,
        _UNDERLINE,
        Color.RED.value,
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=False, italics=True, underline=True
    ).format(use_color=True, use_formatting=True, previous=_Formatting(faint=True)) == [
        _RESET,
        _BOLD,
        _ITALICS,
        _UNDERLINE,
        Color.RED.value,
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=False, underline=True
    ).format(
        use_color=True, use_formatting=True, previous=_Formatting(italics=True)
    ) == [
        _RESET,
        _BOLD,
        _FAINT,
        _UNDERLINE,
        Color.RED.value,
    ]
    assert _Formatting(
        color=Color.RED, bold=True, faint=True, italics=True, underline=False
    ).format(
        use_color=True, use_formatting=True, previous=_Formatting(underline=True)
    ) == [
        _RESET,
        _BOLD,
        _FAINT,
        _ITALICS,
        Color.RED.value,
    ]


def test_color_composer() -> None:
    # empty
    assert (
        ColorComposer(use_color=True, use_formatting=True).add_text("", bold=True).empty
    )
    assert (
        not ColorComposer(use_color=True, use_formatting=True)
        .add_text("foo", bold=True)
        .empty
    )

    assert (
        ColorComposer(use_color=True, use_formatting=True)
        .add_text("foo", bold=True)
        .add_text("bar", faint=True)
        .value
        == f"{_BOLD}foo{_RESET}{_FAINT}bar{_RESET}"
    )
    assert (
        ColorComposer(use_color=True, use_formatting=True)
        .add_text("foo", bold=True)
        .add_text("bar", color=Color.RED)
        .value
        == f"{_BOLD}foo{Color.RED.value}bar{_RESET}"
    )


DETERMINE_MARKER_DATA: list[
    tuple[
        bool,
        int | None,
        tuple[int, int | None],
        tuple[int, int | None] | None,
        str,
        Markings,
        bool,
        bool,
        str,
        str,
        str,
    ]
] = [
    (
        False,
        None,
        (0, None),
        None,
        "  ",
        ASCII_MARKINGS,
        False,
        False,
        "",
        "",
        "  ",
    ),
    (
        True,
        None,
        (0, None),
        None,
        "  ",
        ASCII_MARKINGS,
        True,
        False,
        "",
        "",
        "| ",
    ),
    (
        False,
        123,
        (122, None),
        None,
        "  ",
        ASCII_MARKINGS,
        False,
        False,
        "",
        "",
        "  ",
    ),
    (
        False,
        123,
        (123, None),
        None,
        "  ",
        ASCII_MARKINGS,
        True,
        True,
        "",
        "",
        "> ",
    ),
    (
        False,
        123,
        (123, 3),
        None,
        "  ",
        ASCII_MARKINGS,
        True,
        True,
        "",
        "    ^",
        "  ",
    ),
    (
        False,
        123,
        (123, None),
        (123, None),
        "  ",
        ASCII_MARKINGS,
        True,
        True,
        "/",
        "\\",
        "| ",
    ),
    (
        False,
        123,
        (123, 2),
        (123, 4),
        "  ",
        ASCII_MARKINGS,
        True,
        True,
        "",
        "   ^^",
        "  ",
    ),
    (
        False,
        123,
        (123, 2),
        (124, 4),
        "  ",
        ASCII_MARKINGS,
        True,
        False,
        "/",
        "",
        "| ",
    ),
    (
        True,
        124,
        (123, 2),
        (124, 4),
        "  ",
        ASCII_MARKINGS,
        True,
        True,
        "",
        "\\----/",
        "| ",
    ),
    (
        False,
        123,
        (123, 2),
        (124, None),
        "  ",
        ASCII_MARKINGS,
        True,
        False,
        "/",
        "",
        "| ",
    ),
    (
        True,
        124,
        (123, 2),
        (124, None),
        "  ",
        ASCII_MARKINGS,
        True,
        True,
        "",
        "\\",
        "| ",
    ),
]


@pytest.mark.parametrize(
    "inside, line_no, content_start, content_end, extra_indent, markings, expected_inside,"
    " expected_last_inside, expected_before_mark, expected_after_mark, expected_this_extra_indent",
    DETERMINE_MARKER_DATA,
)
def test__determine_marker(
    inside: bool,
    line_no: int | None,
    content_start: tuple[int, int | None],
    content_end: tuple[int, int | None] | None,
    extra_indent: str,
    markings: Markings,
    expected_inside: bool,
    expected_last_inside: bool,
    expected_before_mark: str,
    expected_after_mark: str,
    expected_this_extra_indent: str,
) -> None:
    result = _determine_marker(
        inside, line_no, content_start, content_end, extra_indent, markings
    )
    assert result == (
        expected_inside,
        expected_last_inside,
        expected_before_mark,
        expected_after_mark,
        expected_this_extra_indent,
    )


RENDER_CODE_DATA: list[
    tuple[
        list[tuple[int | None, str]],
        tuple[int, int | None],
        tuple[int, int | None] | None,
        Markings,
        list[str],
    ]
] = [
    (
        [(None, "foo")],
        (0, None),
        None,
        ASCII_MARKINGS,
        [": |   foo"],
    ),
    (
        [
            (None, ""),
            (3, "foo"),
            (4, "bar"),
            (5, "baz"),
            (6, "bam"),
            (None, ""),
        ],
        (4, None),
        None,
        ASCII_MARKINGS,
        [
            ": |   ",
            "3 |   foo",
            "4 | > bar",
            "5 |   baz",
            "6 |   bam",
            ": |   ",
        ],
    ),
    (
        [
            (None, ""),
            (3, "foo"),
            (4, "bar"),
            (5, "baz"),
            (6, "bam"),
            (None, ""),
        ],
        (4, None),
        (4, None),
        ASCII_MARKINGS,
        [
            ": |   ",
            "3 |   foo",
            "  | /",
            "4 | | bar",
            "  | \\",
            "5 |   baz",
            "6 |   bam",
            ": |   ",
        ],
    ),
    (
        [
            (None, ""),
            (3, "foo"),
            (4, "bar"),
            (5, "baz"),
            (6, "bam"),
            (None, ""),
        ],
        (4, None),
        (5, None),
        ASCII_MARKINGS,
        [
            ": |   ",
            "3 |   foo",
            "  | /",
            "4 | | bar",
            "5 | | baz",
            "  | \\",
            "6 |   bam",
            ": |   ",
        ],
    ),
    (
        [
            (None, ""),
            (3, "foo"),
            (4, "bar"),
            (5, "baz"),
            (6, "bam"),
            (None, ""),
        ],
        (4, 2),
        None,
        ASCII_MARKINGS,
        [
            ": | ",
            "3 | foo",
            "4 | bar",
            "  |  ^",
            "5 | baz",
            "6 | bam",
            ": | ",
        ],
    ),
    (
        [
            (None, ""),
            (3, "foo"),
            (4, "barbam"),
            (5, "baz"),
            (6, "bam"),
            (None, ""),
        ],
        (4, 2),
        (4, 4),
        ASCII_MARKINGS,
        [
            ": | ",
            "3 | foo",
            "4 | barbam",
            "  |  ^^",
            "5 | baz",
            "6 | bam",
            ": | ",
        ],
    ),
    (
        [
            (None, ""),
            (3, "foo"),
            (4, "bar"),
            (5, "baz"),
            (6, "bam"),
            (None, ""),
        ],
        (4, 3),
        (5, 2),
        ASCII_MARKINGS,
        [
            ": |   ",
            "3 |   foo",
            "  | /",
            "4 | | bar",
            "5 | | baz",
            "  | \\--/",
            "6 |   bam",
            ": |   ",
        ],
    ),
]


@pytest.mark.parametrize(
    "content, content_start, content_end, markings, expected_result",
    RENDER_CODE_DATA,
)
def test__render_code(
    content: list[tuple[int | None, str]],
    content_start: tuple[int, int | None],
    content_end: tuple[int, int | None] | None,
    markings: Markings,
    expected_result: list[str],
) -> None:
    result = list(
        _render_code(
            content,
            content_start,
            content_end,
            lambda: ColorComposer(use_color=False, use_formatting=False),
            markings,
        )
    )
    assert result == expected_result


COMPOSE_FIRST_LINE_DATA: list[tuple[Message, str]] = [
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
        ),
        "",
    ),
    (
        Message(
            file=None,
            position=Location(line=1, column=2),
            end_position=Location(line=3, column=4),
            level=Level.INFO,
            id=None,
            message="",
        ),
        "",
    ),
    (
        Message(
            file="foo",
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
        ),
        "foo:",
    ),
    (
        Message(
            file="foo",
            position=Location(line=1, column=None),
            end_position=Location(line=3, column=4),
            level=Level.INFO,
            id=None,
            message="",
        ),
        "foo:1:",
    ),
    (
        Message(
            file="foo",
            position=Location(line=1, column=None, exact=False),
            end_position=Location(line=3, column=4),
            level=Level.INFO,
            id=None,
            message="",
        ),
        "foo:~1:",
    ),
    (
        Message(
            file="foo",
            position=Location(line=1, column=2),
            end_position=Location(line=3, column=4),
            level=Level.INFO,
            id=None,
            message="",
        ),
        "foo:1:2:",
    ),
    (
        Message(
            file="foo",
            position=Location(line=1, column=2, exact=False),
            end_position=Location(line=3, column=4),
            level=Level.INFO,
            id=None,
            message="",
        ),
        "foo:~1:2:",
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id="bar",
            message="",
        ),
        "[bar]",
    ),
    (
        Message(
            file="foo",
            position=None,
            end_position=None,
            level=Level.INFO,
            id="bar",
            message="",
        ),
        "foo: [bar]",
    ),
    (
        Message(
            file="foo",
            position=Location(line=1, column=2),
            end_position=Location(line=3, column=4),
            level=Level.INFO,
            id="bar",
            message="",
        ),
        "foo:1:2: [bar]",
    ),
]


@pytest.mark.parametrize(
    "message, expected_result",
    COMPOSE_FIRST_LINE_DATA,
)
def test__compose_first_line(
    message: Message,
    expected_result: str,
) -> None:
    result = _compose_first_line(
        message, lambda: ColorComposer(use_color=False, use_formatting=False)
    ).value
    assert result == expected_result


COMPOSE_MESSAGE_WITH_NOTE_DATA: list[tuple[Message, str, bool, bool, list[str]]] = [
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
            symbol=None,
            hint=None,
            note=None,
            url=None,
        ),
        "<>",
        False,
        False,
        [],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
            symbol=None,
            hint=None,
            note=None,
            url=None,
        ),
        "<>",
        False,
        True,
        ["<>"],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="foo",
            symbol=None,
            hint=None,
            note=None,
            url=None,
        ),
        "<>",
        False,
        False,
        ["<>foo"],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
            symbol=None,
            hint=None,
            note="foo",
            url=None,
        ),
        "<>",
        False,
        True,
        ["<>Note: foo"],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
            symbol=None,
            hint=None,
            note="foo\nbar",
            url=None,
        ),
        "<>",
        False,
        True,
        ["<>Note: foo", "<>bar"],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
            symbol=None,
            hint="foo",
            note=None,
            url=None,
        ),
        "<>",
        False,
        False,
        [],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="",
            symbol=None,
            hint="foo",
            note=None,
            url=None,
        ),
        "<>",
        False,
        True,
        ["<>"],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="foo\nbar",
            symbol="bam",
            hint="baz",
            note="boom",
            url="bang",
        ),
        "<>",
        False,
        False,
        ["<>foo", "<>bar [bam]", "<>Note: boom"],
    ),
    (
        Message(
            file=None,
            position=None,
            end_position=None,
            level=Level.INFO,
            id=None,
            message="foo\nbar",
            symbol="bam",
            hint="baz",
            note="boom",
            url="bang",
        ),
        "<>",
        True,
        False,
        ["<>foo", "<>bar [bam]", "<>baz", "<>Note: boom"],
    ),
]


@pytest.mark.parametrize(
    "message, indent, add_hint, at_least_one_line, expected_result",
    COMPOSE_MESSAGE_WITH_NOTE_DATA,
)
def test__compose_message_with_note(
    message: Message,
    indent: str,
    add_hint: bool,
    at_least_one_line: bool,
    expected_result: list[str],
) -> None:
    result = list(
        _compose_message_with_note(
            message,
            indent,
            lambda: ColorComposer(use_color=False, use_formatting=False),
            add_hint=add_hint,
            at_least_one_line=at_least_one_line,
        )
    )
    assert result == expected_result
