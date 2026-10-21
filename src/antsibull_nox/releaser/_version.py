# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Version helpers.
"""

from __future__ import annotations

from semantic_version import Version

from ..config import VersionBump


def get_next_version(version: Version, bump: VersionBump) -> Version:
    """
    Given a current version and bump instructions, compute a new version.
    """
    if bump == "next-major":
        return Version(major=version.major + 1, minor=0, patch=0)
    if bump == "next-minor":
        return Version(major=version.major, minor=version.minor + 1, patch=0)
    if bump == "next-bugfix":
        return Version(
            major=version.major, minor=version.minor, patch=version.patch + 1
        )
    if bump == "post-prerelease":
        return Version(
            major=version.major,
            minor=version.minor,
            patch=version.patch,
            prerelease=version.prerelease + ("post0",),
        )
    raise AssertionError(f"Unknown bump value {bump!r}")  # pragma: no cover


__all__ = ("get_next_version",)
