# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

import pytest
from semantic_version import Version

from antsibull_nox.releaser._version import get_next_version

TEST_GET_NEXT_VERSION_DATA: list[tuple[Version, Version, Version, Version, Version]] = [
    (
        Version("1.0.0"),
        Version("2.0.0"),
        Version("1.1.0"),
        Version("1.0.1"),
        Version("1.0.0-post0"),
    ),
    (
        Version("1.2.3-alpha"),
        Version("2.0.0"),
        Version("1.3.0"),
        Version("1.2.4"),
        Version("1.2.3-alpha.post0"),
    ),
    (
        Version("0.1.2-beta.123"),
        Version("1.0.0"),
        Version("0.2.0"),
        Version("0.1.3"),
        Version("0.1.2-beta.123.post0"),
    ),
]


@pytest.mark.parametrize(
    "version, next_major, next_minor, next_bugfix, post_prerelease",
    TEST_GET_NEXT_VERSION_DATA,
)
def test_get_next_version(
    version: Version,
    next_major: Version,
    next_minor: Version,
    next_bugfix: Version,
    post_prerelease: Version,
) -> None:
    assert get_next_version(version, "next-major") == next_major
    assert get_next_version(version, "next-minor") == next_minor
    assert get_next_version(version, "next-bugfix") == next_bugfix
    assert get_next_version(version, "post-prerelease") == post_prerelease
