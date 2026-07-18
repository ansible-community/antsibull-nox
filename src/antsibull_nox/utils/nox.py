# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Information on nox.
"""

from __future__ import annotations

import functools
from importlib.metadata import PackageNotFoundError, version

from . import Version


def _get_package_version(package: str) -> Version | None:
    try:
        return Version.parse(version(package))
    except PackageNotFoundError:
        return None


@functools.cache
def get_nox_version() -> Version | None:
    """
    Get the (major and minor part of the) nox version.
    """
    return _get_package_version("nox")


def is_nox_newer_than(newer_than_version: Version) -> bool:
    """
    Query whether nox is newer (or equally new) than the given version.
    """
    nox_version = get_nox_version()
    if nox_version is None:
        # If there is no version, we assume it's the latest sources of nox,
        # and thus newer than whatever we ask for.
        return True
    return nox_version >= newer_than_version
