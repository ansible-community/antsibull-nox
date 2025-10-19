# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

"""
Tests for the collection module
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import pytest
from antsibull_fileutils.yaml import load_yaml_file

from antsibull_nox.collection.utils import (
    force_collection_version,
)

FORCE_COLLECTION_VERSION_DATA: list[tuple[str, str, bool, dict[str, t.Any]]] = [
    (
        r"""name: foo""",
        "1.2.3",
        True,
        {
            "name": "foo",
            "version": "1.2.3",
        },
    ),
    (
        r"""version: []""",
        "1.2.3",
        True,
        {
            "version": "1.2.3",
        },
    ),
    (
        r"""version: 1.2.2""",
        "1.2.3",
        True,
        {
            "version": "1.2.3",
        },
    ),
    (
        r"""version: 1.2.3""",
        "1.2.3",
        False,
        {
            "version": "1.2.3",
        },
    ),
    (
        r"""
name: boo
namespace: foo
version: null""",
        "1.2.3",
        True,
        {
            "name": "boo",
            "namespace": "foo",
            "version": "1.2.3",
        },
    ),
]


@pytest.mark.parametrize(
    "content, version, expected_result, expected_content",
    FORCE_COLLECTION_VERSION_DATA,
)
def test_force_collection_version(
    content: str,
    version: str,
    expected_result: bool,
    expected_content: dict[str, t.Any],
    tmp_path: Path,
) -> None:
    file = tmp_path / "galaxy.yml"
    file.write_text(content)
    result = force_collection_version(tmp_path, version=version)
    assert result == expected_result
    assert load_yaml_file(file) == expected_content


FORCE_COLLECTION_VERSION_FAIL_DATA: list[tuple[str, str, str]] = [
    (
        r"""{""",
        "1.2.3",
        "^Cannot parse .*/galaxy.yml: ",
    ),
]


@pytest.mark.parametrize(
    "content, version, expected_match",
    FORCE_COLLECTION_VERSION_FAIL_DATA,
)
def test_force_collection_version_fail(
    content: str, version: str, expected_match: str, tmp_path: Path
) -> None:
    file = tmp_path / "galaxy.yml"
    file.write_text(content)
    with pytest.raises(ValueError, match=expected_match):
        force_collection_version(tmp_path, version=version)
