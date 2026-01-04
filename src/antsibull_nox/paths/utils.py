# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Path utilities.
"""

from __future__ import annotations

import atexit
import functools
import os
import shutil
import sys
import typing as t
from collections.abc import Sequence
from pathlib import Path

from antsibull_fileutils.copier import Copier, GitCopier
from antsibull_fileutils.tempfile import (
    ansible_mkdtemp,
    find_tempdir,
    is_acceptable_tempdir,
)
from antsibull_fileutils.vcs import detect_vcs, list_git_files


def find_data_directory() -> Path:
    """
    Retrieve the directory for antsibull_nox.data on disk.
    """
    return Path(__file__).parent.parent / "data"


def path_walk(
    path: Path, top_down: bool = True, follow_symlinks: bool = False
) -> t.Generator[tuple[Path, list[str], list[str]]]:
    """
    Shim for Path.walk() that falls back to os.walk().
    """
    if hasattr(path, "walk"):
        yield from path.walk(top_down=top_down, follow_symlinks=follow_symlinks)
        return
    for dirpath, dirnames, filenames in os.walk(
        path, topdown=top_down, followlinks=follow_symlinks
    ):
        yield (Path(dirpath), dirnames, filenames)


@functools.cache
def list_all_files() -> list[Path]:
    """
    List all files of interest in the repository.
    """
    directory = Path.cwd()
    vcs = detect_vcs(directory)
    if vcs == "git":
        return [directory / path.decode("utf-8") for path in list_git_files(directory)]
    result = []
    for root, dirs, files in path_walk(directory, top_down=True):
        for file in files:
            result.append(root / file)
        if root == directory and ".nox" in dirs:
            dirs.remove(".nox")
    return result


def remove_path(path: Path) -> None:
    """
    Delete a path.
    """
    if not path.is_symlink() and path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def copy_collection(
    source: Path, destination: Path, *, copy_repo_structure: bool = False
) -> None:
    """
    Copy a collection from source to destination.

    Automatically detect supported VCSs and use their information to avoid
    copying ignored files.
    """
    if destination.exists():
        remove_path(destination)
    vcs = detect_vcs(source)
    copier: Copier
    if vcs == "git":
        copier = GitCopier(copy_repo_structure=copy_repo_structure)
    else:
        copier = Copier()
    copier.copy(source, destination, exclude_root=[".nox", ".tox"])


def _is_acceptable_tempdir(directory: Path, excludes: Sequence[Path]) -> bool:
    # Avoid being inside an ansible_collections tree
    if not is_acceptable_tempdir(directory):
        return False
    # Avoid something that's inside one of the excludes
    for exclude in excludes:
        if directory.is_relative_to(exclude):
            return False
    return True


def get_outside_temp_directory(exclude: Sequence[Path] | Path | None = None) -> Path:
    """
    Find a temporary directory root that's outside the provided path.

    Raises ``ValueError`` in case no candidate was found.
    """
    if exclude is None:
        exclude = [Path.cwd()]
    elif isinstance(exclude, Path):
        exclude = [exclude]
    return find_tempdir(lambda path: _is_acceptable_tempdir(path, exclude))


def create_temp_directory(basename: str) -> Path:
    """
    Create a temporary directory outside an existing ansible_collections tree.
    """
    path = ansible_mkdtemp(prefix=basename)

    def cleanup() -> None:
        remove_path(path)

    atexit.register(cleanup)
    return path


def copy_directory_tree_into(source: Path, destination: Path) -> None:
    """
    Copy the directory tree from ``source`` into the tree at ``destination``.

    If ``destination`` does not yet exist, it will be created first.
    """
    if not source.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for root, _, files in path_walk(source):
        path = destination / root.relative_to(source)
        path.mkdir(exist_ok=True)
        for file in files:
            dest = path / file
            remove_path(dest)
            shutil.copy2(root / file, dest, follow_symlinks=False)


def relative_to_walk_up(path: Path, relative_to: Path) -> Path:
    """
    Path.relative_to()'s walk_up kwarg was only added in Python 3.12.
    This function provides a compatibility shim for older Python versions.
    """
    if sys.version_info < (3, 12):
        return Path(os.path.relpath(path, relative_to))
    return path.relative_to(relative_to, walk_up=True)


__all__ = (
    "copy_collection",
    "copy_directory_tree_into",
    "create_temp_directory",
    "find_data_directory",
    "get_outside_temp_directory",
    "list_all_files",
    "path_walk",
    "relative_to_walk_up",
    "remove_path",
)
