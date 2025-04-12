# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Handle Ansible collections.
"""

from __future__ import annotations

import os
import typing as t
from collections.abc import Iterable
from pathlib import Path

from antsibull_fileutils.yaml import load_yaml_file

from ..paths import copy_collection as _paths_copy_collection
from ..paths import remove_path as _remove
from .data import CollectionData, CollectionSource, SetupResult
from .search import CollectionList, get_collection_list

# Function that runs a command (and fails on non-zero return code)
# and returns a tuple (stdout, stderr)
Runner = t.Callable[[list[str]], tuple[bytes, bytes]]


class _CollectionSources:
    sources: dict[str, CollectionSource]

    def __init__(self):
        self.sources = {}

    def set_source(self, name: str, source: CollectionSource) -> None:
        """
        Set source for collection.
        """
        self.sources[name] = source

    def get_source(self, name: str) -> CollectionSource:
        """
        Get source for collection.
        """
        source = self.sources.get(name)
        if source is None:
            source = CollectionSource(name, name)
        return source


_COLLECTION_SOURCES = _CollectionSources()


def setup_collection_sources(collection_sources: dict[str, CollectionSource]) -> None:
    """
    Setup collection sources.
    """
    for name, source in collection_sources.items():
        _COLLECTION_SOURCES.set_source(name, source)


def _add_all_dependencies(
    collections: dict[str, CollectionData], all_collections: CollectionList
) -> None:
    to_process = list(collections.values())
    while to_process:
        collection = to_process.pop(0)
        for dependency_name in collection.dependencies:
            if dependency_name not in collections:
                dependency_data = all_collections.find(dependency_name)
                if dependency_data is None:
                    raise ValueError(
                        f"Cannot find collection {dependency_name},"
                        f" a dependency of {collection.full_name}!"
                    )
                collections[dependency_name] = dependency_data
                to_process.append(dependency_data)


def _install_collection(collection: CollectionData, path: Path) -> None:
    if path.is_symlink():
        if path.readlink() == collection.path:
            return
        path.unlink()
    else:
        _remove(path)
    path.symlink_to(collection.path)


def _install_current_collection(collection: CollectionData, path: Path) -> None:
    if path.exists() and (path.is_symlink() or not path.is_dir()):
        path.unlink()
    path.mkdir(exist_ok=True)
    present = {p.name for p in path.iterdir()}
    for source_entry in collection.path.iterdir():
        if source_entry.name == ".nox":
            continue
        dest_entry = path / source_entry.name
        if source_entry.name in present:
            present.remove(source_entry.name)
            if dest_entry.is_symlink() and dest_entry.readlink() == source_entry:
                continue
            _remove(dest_entry)
        dest_entry.symlink_to(source_entry)
    for name in present:
        dest_entry = path / name
        _remove(dest_entry)


def _install_collections(
    collections: Iterable[CollectionData], root: Path, *, with_current: bool
) -> None:
    for collection in collections:
        namespace_dir = root / collection.namespace
        namespace_dir.mkdir(exist_ok=True)
        path = namespace_dir / collection.name
        if not collection.current:
            _install_collection(collection, path)
        elif with_current:
            _install_current_collection(collection, path)


def _extract_collections_from_extra_deps_file(path: str | os.PathLike) -> list[str]:
    if not os.path.exists(path):
        return []
    try:
        data = load_yaml_file(path)
        result = []
        if data.get("collections"):
            for index, collection in enumerate(data["collections"]):
                if isinstance(collection, str):
                    result.append(collection)
                    continue
                if not isinstance(collection, dict):
                    raise ValueError(
                        f"Collection entry #{index + 1} must be a string or dictionary"
                    )
                if not isinstance(collection.get("name"), str):
                    raise ValueError(
                        f"Collection entry #{index + 1} does not have a 'name' field of type string"
                    )
                result.append(collection["name"])
        return result
    except Exception as exc:
        raise ValueError(
            f"Error while loading collection dependency file {path}: {exc}"
        ) from exc


def setup_collections(
    destination: str | os.PathLike,
    runner: Runner,
    *,
    extra_collections: list[str] | None = None,
    extra_deps_files: list[str | os.PathLike] | None = None,
    with_current: bool = True,
) -> SetupResult:
    """
    Setup all collections in a tree structure inside the destination directory.
    """
    all_collections = get_collection_list(runner)
    destination_root = Path(destination) / "ansible_collections"
    destination_root.mkdir(exist_ok=True)
    current = all_collections.current
    collections_to_install = {current.full_name: current}
    if extra_collections:
        for collection in extra_collections:
            collection_data = all_collections.find(collection)
            if collection_data is None:
                raise ValueError(
                    f"Cannot find collection {collection} required by the noxfile!"
                )
            collections_to_install[collection_data.full_name] = collection_data
    if extra_deps_files is not None:
        for extra_deps_file in extra_deps_files:
            for collection in _extract_collections_from_extra_deps_file(
                extra_deps_file
            ):
                collection_data = all_collections.find(collection)
                if collection_data is None:
                    raise ValueError(
                        f"Cannot find collection {collection} required in {extra_deps_file}!"
                    )
                collections_to_install[collection_data.full_name] = collection_data
    _add_all_dependencies(collections_to_install, all_collections)
    _install_collections(
        collections_to_install.values(), destination_root, with_current=with_current
    )
    return SetupResult(
        root=destination_root,
        current_collection=current,
        current_path=(
            (destination_root / current.namespace / current.name)
            if with_current
            else None
        ),
    )


def _copy_collection(collection: CollectionData, path: Path) -> None:
    _paths_copy_collection(collection.path, path)


def _copy_collection_rsync_hard_links(
    collection: CollectionData, path: Path, runner: Runner
) -> None:
    _, __ = runner(
        [
            "rsync",
            "-av",
            "--delete",
            "--exclude",
            ".nox",
            "--link-dest",
            str(collection.path) + "/",
            "--",
            str(collection.path) + "/",
            str(path) + "/",
        ]
    )


def setup_current_tree(
    place: str | os.PathLike, current_collection: CollectionData
) -> SetupResult:
    """
    Setup a tree structure with the current collection in it.
    """

    path = Path(place)
    root = path / "ansible_collections"
    root.mkdir(exist_ok=True)
    namespace = root / current_collection.namespace
    namespace.mkdir(exist_ok=True)
    collection = namespace / current_collection.name
    _copy_collection(current_collection, collection)
    # _copy_collection_rsync_hard_links(current_collection, collection, runner)
    return SetupResult(
        root=root,
        current_collection=current_collection,
        current_path=collection,
    )


__all__ = [
    "get_collection_list",
    "setup_collections",
    "setup_current_tree",
    "setup_collection_sources",
]
