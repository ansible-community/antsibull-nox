# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

import re

import pytest

from antsibull_nox.releaser._template import template_string

TEST_TEMPLATE_STRING_DATA: list[tuple[str, dict[str, str], str]] = [
    (
        "",
        {},
        "",
    ),
    (
        "hello world!",
        {},
        "hello world!",
    ),
    (
        "\\\\hello\\t\\{world\\}!\\n",
        {},
        "\\hello\t{world}!\n",
    ),
    (
        "hello{world}!",
        {"world": " world!!"},
        "hello world!!!",
    ),
    (
        "hello\\{{world}!\\n",
        {"world": "moo"},
        "hello{moo!\n",
    ),
]


@pytest.mark.parametrize(
    "template, variables, expected_output", TEST_TEMPLATE_STRING_DATA
)
def test_template_string(
    template: str, variables: dict[str, str], expected_output: str
) -> None:
    assert template_string(template, variables=variables) == expected_output


def e(msg: str) -> str:
    return f"^{re.escape(msg)}$"


TEST_TEMPLATE_STRING_FAIL_DATA: list[tuple[str, dict[str, str], str]] = [
    (
        "f\\",
        {},
        e("Template 'f\\\\' ends with single backslash."),
    ),
    (
        "f\\oo",
        {},
        e("Invalid escape sequence \\o in template 'f\\\\oo'."),
    ),
    (
        "{foo}",
        {"bar": "baz", "bam": "boo"},
        e(
            "Unknown variable 'foo' in template '{foo}'. Known variables are: 'bam', 'bar'"
        ),
    ),
]


@pytest.mark.parametrize(
    "template, variables, match_error", TEST_TEMPLATE_STRING_FAIL_DATA
)
def test_template_string_fail(
    template: str, variables: dict[str, str], match_error: str
) -> None:
    with pytest.raises(ValueError, match=match_error):
        template_string(template, variables=variables)
