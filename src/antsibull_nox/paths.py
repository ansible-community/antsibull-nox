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
from pathlib import Path

from antsibull_fileutils.copier import Copier, GitCopier
from antsibull_fileutils.tempfile import ansible_mkdtemp
from antsibull_fileutils.vcs import detect_vcs, list_git_files


def find_data_directory() -> Path:
    """
    Retrieve the directory for antsibull_nox.data on disk.
    """
    return Path(__file__).parent / "data"


def match_path(path: str, is_file: bool, paths: list[str]) -> bool:
    """
    Check whether a path (that is a file or not) matches a given list of paths.
    """
    for check in paths:
        if check == path:
            return True
        if not is_file:
            if not check.endswith("/"):
                check += "/"
            if path.startswith(check):
                return True
    return False


def restrict_paths(paths: list[str], restrict: list[str]) -> list[str]:
    """
    Restrict a list of paths with a given set of restrictions.
    """
    result = []
    for path in paths:
        is_file = os.path.isfile(path)
        if not is_file and not path.endswith("/"):
            path += "/"
        if not match_path(path, is_file, restrict):
            if not is_file:
                for check in restrict:
                    if check.startswith(path) and os.path.exists(check):
                        result.append(check)
            continue
        result.append(path)
    return result


def _scan_remove_paths(
    path: str, remove: list[str], extensions: list[str] | None
) -> list[str]:
    result = []
    for root, dirs, files in os.walk(path, topdown=True):
        if not root.endswith("/"):
            root += "/"
        if match_path(root, False, remove):
            continue
        if all(not check.startswith(root) for check in remove):
            dirs[:] = []
            result.append(root)
            continue
        for file in files:
            if extensions and os.path.splitext(file)[1] not in extensions:
                continue
            filepath = os.path.normpath(os.path.join(root, file))
            if not match_path(filepath, True, remove):
                result.append(filepath)
        for directory in list(dirs):
            if directory == "__pycache__":
                continue
            dirpath = os.path.normpath(os.path.join(root, directory))
            if match_path(dirpath, False, remove):
                dirs.remove(directory)
                continue
    return result


def remove_paths(
    paths: list[str], remove: list[str], extensions: list[str] | None
) -> list[str]:
    """
    Restrict a list of paths by removing paths.

    If ``extensions`` is specified, only files matching this extension
    will be considered when files need to be explicitly enumerated.
    """
    result = []
    for path in paths:
        is_file = os.path.isfile(path)
        if not is_file and not path.endswith("/"):
            path += "/"
        if match_path(path, is_file, remove):
            continue
        if not is_file and any(check.startswith(path) for check in remove):
            result.extend(_scan_remove_paths(path, remove, extensions))
            continue
        result.append(path)
    return result


def filter_paths(
    paths: list[str],
    /,
    remove: list[str] | None = None,
    restrict: list[str] | None = None,
    extensions: list[str] | None = None,
) -> list[str]:
    """
    Modifies a list of paths by restricting to and/or removing paths.
    """
    if restrict:
        paths = restrict_paths(paths, restrict)
    if remove:
        paths = remove_paths(paths, remove, extensions)
    return [path for path in paths if os.path.exists(path)]


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
    for root, dirs, files in os.walk(directory, topdown=True):
        root_path = Path(root)
        for file in files:
            result.append(root_path / file)
        if root_path == directory and ".nox" in dirs:
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


def copy_collection(source: Path, destination: Path) -> None:
    """
    Copy a collection from source to destination.

    Automatically detect supported VCSs and use their information to avoid
    copying ignored files.
    """
    if destination.exists():
        remove_path(destination)
    vcs = detect_vcs(source)
    copier = {
        "none": Copier,
        "git": GitCopier,
    }.get(vcs, Copier)()
    copier.copy(source, destination, exclude_root=[".nox", ".tox"])


def create_temp_directory(basename: str) -> Path:
    """
    Create a temporary directory outside the nox tree.
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
    for root, _, files in source.walk():
        path = destination / root.relative_to(source)
        path.mkdir(exist_ok=True)
        for file in files:
            dest = path / file
            remove_path(dest)
            shutil.copy2(root / file, dest, follow_symlinks=False)


__all__ = [
    "copy_collection",
    "copy_directory_tree_into",
    "create_temp_directory",
    "filter_paths",
    "find_data_directory",
    "list_all_files",
    "remove_path",
]
