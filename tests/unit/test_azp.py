# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

import pytest

from antsibull_nox.azp import _escape_yaml

ESCAPE_YAML_DATA: list[tuple[str, str]] = [
    (
        "",
        '""',
    ),
    (
        "x",
        "x",
    ),
    (
        "x y.z",
        "x y.z",
    ),
    (
        "1.0",
        '"1.0"',
    ),
    (
        "1\n0",
        r'"1\n0"',
    ),
    (
        "1\\0",
        r'"1\\0"',
    ),
    (
        "1'0",
        r'"1\'0"',
    ),
    (
        '1"0',
        r'"1\"0"',
    ),
    (
        "1\x000",
        r'"1\u00000"',
    ),
    (
        "1\x010",
        r'"1\u00010"',
    ),
    (
        "1\x1f0",
        r'"1\u001f0"',
    ),
]


@pytest.mark.parametrize(
    "value, expected_output",
    ESCAPE_YAML_DATA,
)
def test_version_parse(value: str, expected_output: str) -> None:
    assert _escape_yaml(value) == expected_output
