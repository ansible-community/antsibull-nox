# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Path matchers.
"""

from __future__ import annotations

import dataclasses
import typing as t
from collections.abc import Sequence
from pathlib import Path

from .utils import path_walk


def _split_path(path: Path) -> tuple[str, ...]:
    """
    Split relative path ``path`` into a list of path segments.
    """
    assert not path.anchor
    parts = []
    while path.name:
        parts.append(path.name)
        path = path.parent
    return tuple(reversed(parts))


def _get_common_prefix_length(first: tuple[str, ...], second: tuple[str, ...]) -> int:
    max_prefix_length = min(len(first), len(second))
    for i in range(max_prefix_length):
        if first[i] != second[i]:
            return i
    return max_prefix_length


def _starts_with(what: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    """
    Test whether ``what`` starts with ``prefix``.
    """
    return len(what) >= len(prefix) and all(w == p for w, p in zip(what, prefix))


@dataclasses.dataclass(frozen=True)
class _FileInfo:
    """
    Contains information for a file.
    """

    path: Path
    is_dir: bool

    @classmethod
    def create(cls, path: Path) -> t.Self:
        """
        Create a file info object for a path.
        """
        return cls(path=path, is_dir=path.is_dir())


@dataclasses.dataclass(frozen=True)
class _FileSet:
    """
    Contains a set of files as a list of string tuples and a dictionary with further information.
    """

    files: list[tuple[str, ...]]
    infos: dict[tuple[str, ...], _FileInfo]

    @classmethod
    def create(cls, paths: Sequence[Path]) -> t.Self:
        """
        Create a file set from a sequence of paths.
        """
        files = []
        infos = {}
        for path in paths:
            file = _split_path(path)
            if file not in infos:
                files.append(file)
                infos[file] = _FileInfo.create(path)
        return cls(
            files=files,
            infos=infos,
        )

    def clone(self) -> _FileSet:
        """
        Create a copy of this file set.
        """
        return _FileSet(
            files=list(self.files),
            infos=dict(self.infos),
        )

    def subset(self, files: set[tuple[str, ...]]) -> _FileSet:
        """
        Restrict a file set to a subset of files.
        """
        return _FileSet(
            files=list(files), infos={file: self.infos[file] for file in files}
        )

    def merge_set(self, other: _FileSet) -> None:
        """
        Merge this file set with another one.
        """
        for file, info in other.infos.items():
            if file not in self.infos:
                self.files.append(file)
                self.infos[file] = info

    def merge_paths(self, *, paths: Sequence[Path]) -> None:
        """
        Merge this file set with a sequence of paths.
        """
        for path in paths:
            file = _split_path(path)
            if file not in self.infos:
                self.files.append(file)
                self.infos[file] = _FileInfo.create(path)

    def get_paths(self) -> list[Path]:
        """
        Return a list of ``Path`` object for all contained files.
        """
        return [info.path for info in self.infos.values()]


class _ExtensionChecker:
    """
    Allows to test filenames for a set of extensions.
    """

    def __init__(self, *, extensions: Sequence[str]) -> None:
        """
        Create an extension checker, given a list of extensions (without leading period).
        """
        self._extensions = list({f".{ext}" for ext in extensions})

    def has(self, filename: str) -> bool:
        """
        Test whether the filename has one of our extensions.
        """
        return any(filename.endswith(ext) for ext in self._extensions)


class FileCollector:
    """
    Modifies a list of paths by restricting to and/or removing paths.

    The paths can point to directories or files.
    """

    def __init__(self, *, paths: list[Path]) -> None:
        """
        Create a list of paths.
        """
        self._paths = _FileSet.create(paths)

    def restrict(self, *, paths: list[Path]) -> None:
        """
        Restrict the list of paths to the given list of paths.
        """
        paths_set = _FileSet.create(paths)
        files: set[tuple[str, ...]] = set()
        path_files: set[tuple[str, ...]] = set()
        for file in self._paths.files:
            for path in paths_set.files:
                cpl = _get_common_prefix_length(file, path)
                if cpl == len(path):
                    files.add(file)
                    break
                if cpl == len(file):
                    path_files.add(path)
        self._paths = self._paths.subset(files)
        if path_files:
            self._paths.merge_set(paths_set.subset(path_files))

    @staticmethod
    def _match(file: tuple[str, ...], paths_set: _FileSet) -> bool:
        return any(_starts_with(file, other) for other in paths_set.files)

    def _scan_remove_paths(
        self, path: Path, *, remove: _FileSet, extensions: _ExtensionChecker | None
    ) -> list[Path]:
        result = []
        for root, dirs, files in path_walk(path, top_down=True):
            root_file = _split_path(root)
            if self._match(root_file, remove):
                # This should never happen anyway, since it's already covered by other cases
                dirs[:] = []  # pragma: no cover
                continue  # pragma: no cover
            if all(not _starts_with(check, root_file) for check in remove.files):
                dirs[:] = []  # do not iterate deeper
                result.append(root)
                continue
            for file in files:
                if extensions and not extensions.has(file):
                    continue
                file_file = root_file + (file,)
                if not self._match(file_file, remove):
                    result.append(root / file)
            for directory in list(dirs):
                # We should probably use .gitignore here...
                if directory == "__pycache__":
                    dirs.remove(directory)
                    continue
                directory_file = root_file + (directory,)
                if self._match(directory_file, remove):
                    dirs.remove(directory)
                    continue
        return result

    def remove(self, *, paths: list[Path], extensions: list[str] | None = None) -> None:
        """
        Restrict/refine the list of paths by removing a given list of paths.

        If ``extensions`` is provided, during refinement only files with extensions
        in the given list are added.
        """
        extensions_checker = (
            _ExtensionChecker(extensions=extensions) if extensions is not None else None
        )
        paths_set = _FileSet.create(paths)
        files = set()
        other_files = []
        for file, info in self._paths.infos.items():
            remove_file = False
            remove_subset = []
            for path in paths_set.files:
                cpl = _get_common_prefix_length(file, path)
                if cpl == len(path):
                    remove_file = True
                    break
                if cpl == len(file):
                    remove_subset.append(path)
            if remove_file:
                continue
            if not info.is_dir or not remove_subset:
                files.add(file)
                continue
            other_files.extend(
                self._scan_remove_paths(
                    info.path, remove=paths_set, extensions=extensions_checker
                )
            )
        self._paths = self._paths.subset(files)
        if other_files:
            self._paths.merge_paths(paths=other_files)

    def get_paths(self) -> list[Path]:
        """
        Return the list of paths.
        """
        return self._paths.get_paths()

    def get_existing(self) -> list[Path]:
        """
        Return the list of paths that actually exist.
        """
        return [path for path in self._paths.get_paths() if path.exists()]


__all__ = ("FileCollector",)
