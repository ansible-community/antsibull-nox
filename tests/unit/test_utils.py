# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

import pytest

from antsibull_nox.utils import Version, version_range

VERSION_PARSE_DATA: list[tuple[str, Version]] = [
    (
        "1.2",
        Version(1, 2),
    ),
    (
        "1.2.3b1",
        Version(1, 2),
    ),
]


@pytest.mark.parametrize(
    "version_string, expected_version",
    VERSION_PARSE_DATA,
)
def test_version_parse(version_string: str, expected_version: Version) -> None:
    assert Version.parse(version_string) == expected_version


def test_verison_parse_fail() -> None:
    with pytest.raises(ValueError, match=r"^Cannot parse '1' as version string\.$"):
        Version.parse("1")

    with pytest.raises(ValueError, match=r"^Cannot parse '1.a' as version string.$"):
        Version.parse("1.a")


def test_version_next() -> None:
    assert Version(2, 3).next_minor_version() == Version(2, 4)
    assert Version(1, 9).next_minor_version() == Version(1, 10)


def test_version_prev() -> None:
    assert Version(2, 4).previous_minor_version() == Version(2, 3)
    assert Version(1, 10).previous_minor_version() == Version(1, 9)

    with pytest.raises(ValueError, match="^No previous minor version exists$"):
        Version(1, 0).previous_minor_version()


VERSION_RANGE_DATA: list[tuple[str, str, bool, list[str]]] = [
    (
        "1.2",
        "1.3",
        True,
        ["1.2", "1.3"],
    ),
    (
        "1.2",
        "1.3",
        False,
        ["1.2"],
    ),
]


@pytest.mark.parametrize(
    "start, end, inclusive, expected_versions",
    VERSION_RANGE_DATA,
)
def test_version_range(
    start: str, end: str, inclusive: bool, expected_versions: list[str]
) -> None:
    sv = Version.parse(start)
    ev = Version.parse(end)
    evs = [Version.parse(v) for v in expected_versions]
    versions = [v for v in version_range(sv, ev, inclusive=inclusive)]
    assert versions == evs


def test_version_range_fail() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"^Cannot list all versions from 1\.2 to 2\.3"
            r" since they have different major versions$"
        ),
    ):
        next(version_range(Version(1, 2), Version(2, 3), inclusive=True))
