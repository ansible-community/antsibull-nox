# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Path utils for creating nox sessions.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ...cd import get_changes
from ...paths import filter_paths as _filter_paths
from ...paths import (
    restrict_paths,
)


def filter_paths(
    paths: list[str],
    /,
    remove: list[str] | None = None,
    restrict: list[str] | None = None,
    extensions: list[str] | None = None,
    with_cd: bool = False,
) -> list[str]:
    """
    Modifies a list of paths by restricting to and/or removing paths.
    """
    if with_cd:
        changed_files = get_changes(relative_to=Path.cwd())
        if changed_files is not None:
            restrict_cd = [str(file) for file in changed_files]
            paths = restrict_paths(paths, restrict_cd)
    return _filter_paths(paths, remove=remove, restrict=restrict, extensions=extensions)


def filter_files_cd(files: Sequence[Path]) -> list[Path]:
    """
    Given a sequence of paths, filters out changed files if change detection is enabled.
    If it is disabled, simply return the sequence as a list.
    """
    changed_files = get_changes(relative_to=Path.cwd())
    if changed_files is None:
        if isinstance(files, list):
            return files
        return list(files)

    changed_set = set(changed_files)
    return [file for file in files if file in changed_set]


__all__ = [
    "filter_files_cd",
    "filter_paths",
]
