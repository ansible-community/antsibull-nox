# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
General utilities.
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass


@dataclass(order=True, frozen=True)
class Version:
    """
    Models a two-part version (major and minor).
    """

    major: int
    minor: int

    @classmethod
    def parse(cls, version_string: str) -> Version:
        """
        Given a version string, parses it into a Version object.
        Other components than major and minor version are ignored.
        """
        try:
            major, minor = [int(v) for v in version_string.split(".")[:2]]
        except (AttributeError, ValueError) as exc:
            raise ValueError(
                f"Cannot parse {version_string!r} as version string."
            ) from exc
        return Version(major=major, minor=minor)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    def next_minor_version(self) -> Version:
        """
        Returns the next minor version.

        The major version stays the same, and the minor version is increased by 1.
        """
        return Version(self.major, self.minor + 1)

    def previous_minor_version(self) -> Version:
        """
        Returns the previous minor version.
        Raises a ValueError if there is none.

        The major version stays the same, and the minor version is decreased by 1.
        """
        if self.minor == 0:
            raise ValueError("No previous minor version exists")
        return Version(self.major, self.minor - 1)


def version_range(
    start: Version, end: Version, *, inclusive: bool
) -> t.Generator[Version]:
    """
    Enumerate all versions starting at ``start`` until ``end``.

    Whether ``end`` is included in the range depends on ``inclusive``.
    """
    if start.major != end.major:
        raise ValueError(
            f"Cannot list all versions from {start} to {end}"
            " since they have different major versions"
        )
    version = start
    while (version <= end) if inclusive else (version < end):
        yield version
        version = Version(major=version.major, minor=version.minor + 1)


__all__ = [
    "Version",
    "version_range",
]
