# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

import pytest

from antsibull_nox.messages.utils import find_json, find_json_line

FIND_JSON_DATA: list[tuple[str, str]] = [
    (
        r"""""",
        r"""""",
    ),
    (
        r"""foo""",
        r"""foo""",
    ),
    (
        r"""
foo
[bar]
baz
""",
        r"""[bar]""",
    ),
    (
        r"""
{foo}
[bar]
{baz}
""",
        r"""{foo}
[bar]
{baz}""",
    ),
    (
        r"""
{foo
[bar]
baz}
""",
        r"""{foo
[bar]
baz}""",
    ),
    (
        r"""
foo {
  {
foo
}
[
]
""",
        r"""  {
foo
}""",
    ),
    (
        r"""{""",
        r"""{""",
    ),
    (
        r"""
foo
{
bar
""",
        r"""
foo
{
bar
""",
    ),
]


@pytest.mark.parametrize(
    "output, expected_result",
    FIND_JSON_DATA,
)
def test_find_json(output: str, expected_result: str) -> None:
    assert find_json(output) == expected_result


FIND_JSON_LINE_DATA: list[tuple[str, str]] = [
    (
        r"""""",
        r"""""",
    ),
    (
        r"""{foo}""",
        r"""{foo}""",
    ),
    (
        r"""[foo]""",
        r"""[foo]""",
    ),
    (
        r"""
{foo}
[bar]
{baz}
""",
        r"""{foo}""",
    ),
    (
        r"""
{foo
[bar]
baz}
""",
        r"""[bar]""",
    ),
    (
        r"""
bar
[foo
""",
        r"""
bar
[foo
""",
    ),
]


@pytest.mark.parametrize(
    "output, expected_result",
    FIND_JSON_LINE_DATA,
)
def test_find_json_line(output: str, expected_result: str) -> None:
    assert find_json_line(output) == expected_result
