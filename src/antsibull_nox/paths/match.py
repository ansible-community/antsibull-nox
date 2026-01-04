# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Path matchers.
"""

from __future__ import annotations

import dataclasses
import typing as t
from collections.abc import Iterable
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
    def create(cls, paths: Iterable[Path]) -> t.Self:
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

    @classmethod
    def create_from_split(cls, *, split_files: Iterable[tuple[str, ...]]) -> t.Self:
        """
        Create a file set from a sequence of split paths.
        """
        files = []
        infos = {}
        root = Path(".")
        for file in split_files:
            if file not in infos:
                files.append(file)
                infos[file] = _FileInfo.create(root.joinpath(*file))
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

    def merge_paths(self, *, paths: Iterable[Path]) -> None:
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

    def __init__(self, *, extensions: Iterable[str]) -> None:
        """
        Create an extension checker, given a list of extensions (without leading period).
        """
        self._extensions = list({f".{ext}" for ext in extensions})

    def has(self, filename: str) -> bool:
        """
        Test whether the filename has one of our extensions.
        """
        return any(filename.endswith(ext) for ext in self._extensions)


@dataclasses.dataclass(frozen=False)
class _FileTreeNode:
    """
    Represent a node in a file tree.
    """

    file: tuple[str, ...]
    contained: bool
    children: dict[str, _FileTreeNode]

    def iterate(self) -> t.Generator[tuple[str, ...]]:
        """
        Generate all contained files.
        """
        if self.contained:
            yield self.file
        for child in self.children.values():
            yield from child.iterate()


@dataclasses.dataclass(frozen=False)
class _FileTree:
    """
    Represent a set of files as a hierarchical tree.
    """

    root: _FileTreeNode

    def __init__(self) -> None:
        self.root = _FileTreeNode(file=(), contained=False, children={})

    def add(self, file: tuple[str, ...], *, keep_pruned: bool = False) -> None:
        """
        Add a file to the tree.

        If ``keep_pruned == True``, all children below an entry will be removed.
        """
        node = self.root
        for index, part in enumerate(file):
            if keep_pruned and node.contained:
                return
            next_node = node.children.get(part)
            if next_node is None:
                next_node = _FileTreeNode(
                    file=file[: index + 1], contained=False, children={}
                )
                node.children[part] = next_node
            node = next_node
        node.contained = True
        if keep_pruned:
            node.children.clear()

    @classmethod
    def create_from_files(
        cls, files: Iterable[tuple[str, ...]], *, keep_pruned: bool = False
    ) -> t.Self:
        """
        Create a file tree from a sequence of files.
        """
        result = cls()
        for file in files:
            result.add(file, keep_pruned=keep_pruned)
        return result

    @classmethod
    def create_from_paths(
        cls, paths: Iterable[Path], *, keep_pruned: bool = False
    ) -> t.Self:
        """
        Create a file tree from a sequence of paths.
        """
        result = cls()
        for path in paths:
            file = _split_path(path)
            result.add(file, keep_pruned=keep_pruned)
        return result

    def find_closest(self, file: tuple[str, ...]) -> tuple[tuple[str, ...], bool]:
        """
        Find the closest match to the file in the tree.

        Return a tuple ``(closest_match, closest_match_contained_in_tree)``.
        """
        node = self.root
        for part in file:
            next_node = node.children.get(part)
            if next_node is None:
                break
            node = next_node
        return node.file, node.contained

    def has_or_has_children(self, file: tuple[str, ...]) -> bool:
        """
        Check if a file is part of the tree, or has children inside the tree
        (i.e. files in the tree start with the given file).
        """
        path, _contained = self.find_closest(file)
        return len(path) == len(file)

    def has_or_is_child(self, file: tuple[str, ...]) -> bool:
        """
        Check if a file is part of the tree, or is a child of something in the tree.
        """
        node = self.root
        for part in file:
            if node.contained:
                return True
            next_node = node.children.get(part)
            if next_node is None:
                return False
            node = next_node
        return node.contained

    def iterate(
        self, *, prefix: tuple[str, ...] | None = None
    ) -> t.Generator[tuple[str, ...]]:
        """
        Generate all contained files.
        """
        node = self.root
        if prefix is not None:
            for part in prefix:
                next_node = node.children.get(part)
                if next_node is None:
                    return
                node = next_node
        yield from node.iterate()


class FileCollector:
    """
    Modifies a list of paths by restricting to and/or removing paths.

    The paths can point to directories or files.
    """

    def __init__(self, *, paths: list[Path] | _FileSet) -> None:
        """
        Create a list of paths.
        """
        self._paths = paths if isinstance(paths, _FileSet) else _FileSet.create(paths)

    def clone(self) -> FileCollector:
        """
        Create a copy of the file collector.
        """
        return FileCollector(paths=self._paths.clone())

    @classmethod
    def create(cls, sources: Iterable[str], *, glob: bool = True) -> t.Self:
        """
        Create a list of paths from strings with potential globbing.
        """
        # Collect files in tree
        tree = _FileTree()
        root = Path(".")
        for source in sources:
            if glob:
                for path in root.glob(source):
                    tree.add(_split_path(path), keep_pruned=True)
            else:
                tree.add(_split_path(Path(source)), keep_pruned=True)
        # Create set
        return cls(paths=_FileSet.create_from_split(split_files=list(tree.iterate())))

    @staticmethod
    def _get_pruned_tree(paths: list[Path] | FileCollector) -> _FileTree:
        if isinstance(paths, FileCollector):
            return _FileTree.create_from_files(
                paths._paths.files, keep_pruned=True  # pylint: disable=protected-access
            )
        return _FileTree.create_from_paths(paths, keep_pruned=True)

    def restrict(self, *, paths: list[Path] | FileCollector) -> None:
        """
        Restrict the list of paths to the given list of paths.
        """
        paths_tree = self._get_pruned_tree(paths)
        files: set[tuple[str, ...]] = set()
        path_files: set[tuple[str, ...]] = set()
        for file in self._paths.files:
            path, contained = paths_tree.find_closest(file)
            if contained:
                files.add(file)
            elif len(path) == len(file):
                path_files.update(paths_tree.iterate(prefix=path))
        self._paths = self._paths.subset(files)
        if path_files:
            self._paths.merge_set(_FileSet.create_from_split(split_files=path_files))

    def _scan_remove_paths(
        self, path: Path, *, remove: _FileTree, extensions: _ExtensionChecker | None
    ) -> list[Path]:
        result = []
        for root, dirs, files in path_walk(path, top_down=True):
            root_file = _split_path(root)
            if remove.has_or_is_child(root_file):
                # This should never happen anyway, since it's already covered by other cases
                dirs[:] = []  # pragma: no cover
                continue  # pragma: no cover
            if not remove.has_or_has_children(root_file):
                dirs[:] = []  # do not iterate deeper
                result.append(root)
                continue
            for file in files:
                if extensions and not extensions.has(file):
                    continue
                file_file = root_file + (file,)
                if not remove.has_or_is_child(file_file):
                    result.append(root / file)
            for directory in list(dirs):
                # We should probably use .gitignore here...
                if directory == "__pycache__":
                    dirs.remove(directory)
                    continue
                directory_file = root_file + (directory,)
                if remove.has_or_is_child(directory_file):
                    dirs.remove(directory)
                    continue
        return result

    def remove(
        self, *, paths: list[Path] | FileCollector, extensions: list[str] | None = None
    ) -> None:
        """
        Restrict/refine the list of paths by removing a given list of paths.

        If ``extensions`` is provided, during refinement only files with extensions
        in the given list are added.
        """
        extensions_checker = (
            _ExtensionChecker(extensions=extensions) if extensions is not None else None
        )
        paths_tree = self._get_pruned_tree(paths)
        files = set()
        other_files = []
        for file, info in self._paths.infos.items():
            path, contained = paths_tree.find_closest(file)
            if contained:
                continue
            if not info.is_dir or len(path) != len(file):
                files.add(file)
                continue
            other_files.extend(
                self._scan_remove_paths(
                    info.path, remove=paths_tree, extensions=extensions_checker
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
