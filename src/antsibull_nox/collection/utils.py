# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Build Ansible collections.
"""

from __future__ import annotations

from pathlib import Path

from antsibull_fileutils.yaml import load_yaml_file, store_yaml_file

from .search import GALAXY_YML


def force_collection_version(path: Path, *, version: str) -> bool:
    """
    Make sure galaxy.yml contains this version.

    Returns ``True`` if the version was changed, and ``False`` if the version
    was already set to this value.
    """
    galaxy_yml = path / GALAXY_YML
    try:
        data = load_yaml_file(galaxy_yml)
    except Exception as exc:
        raise ValueError(f"Cannot parse {galaxy_yml}: {exc}") from exc
    if data.get("version") == version:
        return False
    data["version"] = version
    store_yaml_file(galaxy_yml, data)
    return True


__all__ = [
    "force_collection_version",
]
