# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Path utils for creating nox sessions.
"""

from __future__ import annotations

import typing as t
from collections.abc import Sequence
from pathlib import Path

from ...cd import get_changes
from ...paths.match import FileCollector
from ...python.python_dependencies import get_python_dependency_info

PythonDependencies = t.Literal["none", "imported-by-changed", "importing-changed"]


def add_python_deps(files: list[Path], *, forward: bool, cwd: Path) -> None:
    """
    Given a list of files, add all Python files that (transitively) import
    these (``forward == False``) or are imported by them (``forward == True``).
    """
    deps_info = get_python_dependency_info()
    next_modules_dict = (
        deps_info.file_to_imported_modules
        if forward
        else deps_info.file_to_imported_by_modules
    )
    added = {
        (file if file.is_absolute() else cwd / file)
        for file in files
        if file.name.endswith(".py")
    }
    processed = set()
    to_process = set(added)
    while to_process:
        elt = to_process.pop()
        if elt in processed:
            continue
        processed.add(elt)
        if elt not in added:
            if elt.is_relative_to(cwd):
                files.append(elt.relative_to(cwd))
                added.add(elt)
        next_module_paths = next_modules_dict.get(elt)
        if next_module_paths is None:
            continue
        for next_module in next_module_paths[1]:
            if next_module not in added and next_module not in processed:
                to_process.add(next_module)


def filter_paths(
    paths: list[Path] | FileCollector,
    /,
    remove: list[Path] | FileCollector | None = None,
    restrict: list[Path] | FileCollector | None = None,
    extensions: list[str] | None = None,
    with_cd: bool = False,
    cd_add_python_deps: PythonDependencies = "none",
) -> list[Path]:
    """
    Modifies a list of paths by restricting to and/or removing paths.
    """
    collector = (
        paths.clone()
        if isinstance(paths, FileCollector)
        else FileCollector(paths=[Path(path) for path in paths])
    )
    if with_cd:
        cwd = Path.cwd()
        changed_files = get_changes(relative_to=cwd)
        if changed_files is not None:
            if cd_add_python_deps != "none":
                add_python_deps(
                    changed_files,
                    forward=cd_add_python_deps == "imported-by-changed",
                    cwd=cwd,
                )
            if extensions:
                changed_files = [
                    file for file in changed_files if file.suffix in extensions
                ]
            collector.restrict(paths=changed_files)
    if restrict:
        collector.restrict(paths=restrict)
    if remove:
        collector.remove(paths=remove, extensions=extensions)
    return collector.get_existing()


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
    "add_python_deps",
    "filter_files_cd",
    "filter_paths",
]
