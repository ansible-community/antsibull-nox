# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Handle Ansible collections.
"""

from __future__ import annotations

import json
import os
import threading
import typing as t
from collections.abc import Collection, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from antsibull_fileutils.yaml import load_yaml_file

from .data import CollectionData

# Function that runs a command (and fails on non-zero return code)
# and returns a tuple (stdout, stderr)
Runner = t.Callable[[list[str]], tuple[bytes, bytes]]


@dataclass(frozen=True)
class _GlobalCache:
    root: Path
    download_cache: Path
    extracted_cache: Path

    @classmethod
    def create(cls, *, root: Path) -> _GlobalCache:
        """
        Create a global cache object.
        """
        return cls(
            root=root,
            download_cache=root / "downloaded",
            extracted_cache=root / "extracted",
        )


def _load_galaxy_yml(galaxy_yml: Path) -> dict[str, t.Any]:
    try:
        data = load_yaml_file(galaxy_yml)
    except Exception as exc:
        raise ValueError(f"Cannot parse {galaxy_yml}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{galaxy_yml} is not a dictionary")
    return data


def _load_manifest_json_collection_info(manifest_json: Path) -> dict[str, t.Any]:
    try:
        with open(manifest_json, "br") as f:
            data = json.load(f)
    except Exception as exc:
        raise ValueError(f"Cannot parse {manifest_json}: {exc}") from exc
    ci = data.get("collection_info")
    if not isinstance(ci, dict):
        raise ValueError(f"{manifest_json} does not contain collection_info")
    return ci


def load_collection_data_from_disk(
    path: Path,
    *,
    namespace: str | None = None,
    name: str | None = None,
    root: Path | None = None,
    current: bool = False,
    accept_manifest: bool = True,
) -> CollectionData:
    """
    Load collection data from disk.
    """
    galaxy_yml = path / "galaxy.yml"
    manifest_json = path / "MANIFEST.json"
    found: Path
    if galaxy_yml.is_file():
        found = galaxy_yml
        data = _load_galaxy_yml(galaxy_yml)
    elif not accept_manifest:
        raise ValueError(f"Cannot find galaxy.yml in {path}")
    elif manifest_json.is_file():
        found = manifest_json
        data = _load_manifest_json_collection_info(manifest_json)
    else:
        raise ValueError(f"Cannot find galaxy.yml or MANIFEST.json in {path}")

    ns = data.get("namespace")
    if not isinstance(ns, str):
        raise ValueError(f"{found} does not contain a namespace")
    n = data.get("name")
    if not isinstance(n, str):
        raise ValueError(f"{found} does not contain a name")
    v = data.get("version")
    if not isinstance(v, str):
        v = None
    d = data.get("dependencies") or {}
    if not isinstance(d, dict):
        raise ValueError(f"{found}'s dependencies is not a mapping")

    if namespace is not None and ns != namespace:
        raise ValueError(
            f"{found} contains namespace {ns!r}, but was hoping for {namespace!r}"
        )
    if name is not None and n != name:
        raise ValueError(f"{found} contains name {n!r}, but was hoping for {name!r}")
    return CollectionData(
        collections_root_path=root,
        path=path,
        namespace=ns,
        name=n,
        full_name=f"{ns}.{n}",
        version=v,
        dependencies=d,
        current=current,
    )


def _list_adjacent_collections_ansible_collections_tree(
    root: Path,
    *,
    directories_to_ignore: Collection[Path] | None = None,
) -> Iterator[CollectionData]:
    directories_to_ignore = directories_to_ignore or ()
    for namespace in root.iterdir():  # pylint: disable=too-many-nested-blocks
        try:
            if namespace.is_dir() or namespace.is_symlink():
                for name in namespace.iterdir():
                    if name in directories_to_ignore:
                        continue
                    try:
                        if name.is_dir() or name.is_symlink():
                            yield load_collection_data_from_disk(
                                name,
                                namespace=namespace.name,
                                name=name.name,
                                root=root,
                            )
                    except Exception:  # pylint: disable=broad-exception-caught
                        # If name doesn't happen to be a (symlink to a) directory,
                        # is not readable, ...
                        pass
        except Exception:  # pylint: disable=broad-exception-caught
            # If namespace doesn't happen to be a (symlink to a) directory, is not readable, ...
            pass


def _list_adjacent_collections_outside_tree(
    directory: Path,
    *,
    directories_to_ignore: Collection[Path] | None = None,
) -> Iterator[CollectionData]:
    directories_to_ignore = directories_to_ignore or ()
    for collection_dir in directory.iterdir():
        if collection_dir in directories_to_ignore:
            continue
        if not collection_dir.is_dir() and not collection_dir.is_symlink():
            continue
        parts = collection_dir.name.split(".")
        if len(parts) != 2:
            continue
        namespace, name = parts
        if not namespace.isidentifier() or not name.isidentifier():
            continue
        try:
            yield load_collection_data_from_disk(
                collection_dir,
                namespace=namespace,
                name=name,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # If collection_dir doesn't happen to be a (symlink to a) directory, ...
            pass


def _fs_list_local_collections() -> Iterator[CollectionData]:
    root: Path | None = None

    # Determine potential root
    cwd = Path.cwd()
    parents: Sequence[Path] = cwd.parents
    if len(parents) > 2 and parents[1].name == "ansible_collections":
        root = parents[1]

    # Current collection
    try:
        current = load_collection_data_from_disk(cwd, root=root, current=True)
        if root and current.namespace == parents[0].name and current.name == cwd.name:
            yield current
        else:
            root = None
            current = load_collection_data_from_disk(cwd, current=True)
            yield current
    except Exception as exc:
        raise ValueError(
            f"Cannot load current collection's info from {cwd}: {exc}"
        ) from exc

    # Search tree
    if root:
        yield from _list_adjacent_collections_ansible_collections_tree(
            root, directories_to_ignore=(cwd,)
        )
    elif len(parents) > 0:
        yield from _list_adjacent_collections_outside_tree(
            parents[0], directories_to_ignore=(cwd,)
        )
    else:
        # Only happens if cwd == "/"
        pass  # pragma: no cover


def _fs_list_global_cache(global_cache_dir: Path) -> Iterator[CollectionData]:
    if not global_cache_dir.is_dir():
        return

    yield from _list_adjacent_collections_outside_tree(global_cache_dir)


def _galaxy_list_collections(runner: Runner) -> Iterator[CollectionData]:
    try:
        stdout, _ = runner(["ansible-galaxy", "collection", "list", "--format", "json"])
        data = json.loads(stdout)
        for collections_root_path, collections in data.items():
            root = Path(collections_root_path)
            for collection in collections:
                namespace, name = collection.split(".", 1)
                try:
                    yield load_collection_data_from_disk(
                        root / namespace / name,
                        namespace=namespace,
                        name=name,
                        root=root,
                        current=False,
                    )
                except:  # noqa: E722, pylint: disable=bare-except
                    # Looks like Ansible passed crap on to us...
                    pass
    except Exception as exc:
        raise ValueError(f"Error while loading collection list: {exc}") from exc


@dataclass
class CollectionList:
    """
    A list of Ansible collections.
    """

    collections: list[CollectionData]
    collection_map: dict[str, CollectionData]
    current: CollectionData

    @classmethod
    def create(cls, collections_map: dict[str, CollectionData]):
        """
        Given a dictionary mapping collection names to collection data, creates a CollectionList.

        One of the collections must have the ``current`` flag set.
        """
        collections = sorted(collections_map.values(), key=lambda cli: cli.full_name)
        current = next(c for c in collections if c.current)
        return cls(
            collections=collections,
            collection_map=collections_map,
            current=current,
        )

    @classmethod
    def collect(cls, *, runner: Runner, global_cache: _GlobalCache) -> CollectionList:
        """
        Search for a list of collections. The result is not cached.
        """
        found_collections = {}
        for collection_data in _fs_list_local_collections():
            found_collections[collection_data.full_name] = collection_data
        if os.environ.get("ANTSIBULL_NOX_IGNORE_INSTALLED_COLLECTIONS") != "true":
            for collection_data in _galaxy_list_collections(runner):
                # Similar to Ansible, we use the first match
                if collection_data.full_name not in found_collections:
                    found_collections[collection_data.full_name] = collection_data
        for collection_data in _fs_list_global_cache(global_cache.extracted_cache):
            # Similar to Ansible, we use the first match
            if collection_data.full_name not in found_collections:
                found_collections[collection_data.full_name] = collection_data
        return cls.create(found_collections)

    def find(self, name: str) -> CollectionData | None:
        """
        Find a collection for a given name.
        """
        return self.collection_map.get(name)

    def clone(self) -> CollectionList:
        """
        Create a clone of this list.
        """
        return CollectionList(
            collections=list(self.collections),
            collection_map=dict(self.collection_map),
            current=self.current,
        )

    def _add(self, collection: CollectionData, *, force: bool = True) -> bool:
        if not force and collection.full_name in self.collection_map:
            return False
        self.collections.append(collection)
        self.collection_map[collection.full_name] = collection
        return True


class _CollectionListUpdater:
    def __init__(
        self, *, owner: "_CollectionListSingleton", collection_list: CollectionList
    ) -> None:
        self._owner = owner
        self._collection_list = collection_list

    def find(self, name: str) -> CollectionData | None:
        """
        Find a collection for a given name.
        """
        return self._collection_list.find(name)

    def add_collection(
        self, *, directory: Path, namespace: str, name: str
    ) -> CollectionData:
        """
        Add a new collection to the cache.
        """
        # pylint: disable-next=protected-access
        return self._owner._add_collection(
            directory=directory, namespace=namespace, name=name
        )

    def get_global_cache(self) -> _GlobalCache:
        """
        Get the global cache object.
        """
        return self._owner._get_global_cache()  # pylint: disable=protected-access


class _CollectionListSingleton:
    _lock = threading.Lock()

    _global_cache_dir: Path | None = None
    _collection_list: CollectionList | None = None

    def setup(self, *, global_cache_dir: Path) -> None:
        """
        Setup data.
        """
        with self._lock:
            if (
                self._global_cache_dir is not None
                and self._global_cache_dir != global_cache_dir
            ):
                raise ValueError(
                    "Setup mismatch: global cache dir cannot be both"
                    f" {self._global_cache_dir} and {global_cache_dir}"
                )
            self._global_cache_dir = global_cache_dir

    def clear(self) -> None:
        """
        Clear collection cache.
        """
        with self._lock:
            self._collection_list = None

    def get_cached(self) -> CollectionList | None:
        """
        Return cached list of collections, if present.
        Do not modify the result!
        """
        return self._collection_list

    def get(self, *, runner: Runner) -> CollectionList:
        """
        Search for a list of collections. The result is cached.
        """
        with self._lock:
            if self._global_cache_dir is None:
                raise ValueError("Internal error: global cache dir not setup")
            result = self._collection_list
            if result is None:
                result = CollectionList.collect(
                    runner=runner,
                    global_cache=_GlobalCache.create(root=self._global_cache_dir),
                )
                self._collection_list = result
        return result.clone()

    def _get_global_cache(self) -> _GlobalCache:
        """
        Returns the global cache dir.
        """
        if self._global_cache_dir is None:
            raise ValueError("Internal error: global cache dir not setup")
        return _GlobalCache.create(root=self._global_cache_dir)

    def _add_collection(
        self, *, directory: Path, namespace: str, name: str
    ) -> CollectionData:
        """
        Add collection in directory if the collection list has been cached.
        """
        if not self._collection_list:
            raise ValueError("Internal error: collections not listed")
        data = load_collection_data_from_disk(directory, namespace=namespace, name=name)
        self._collection_list._add(data)  # pylint: disable=protected-access
        return data

    @contextmanager
    def _update_collection_list(self) -> t.Iterator[_CollectionListUpdater]:
        with self._lock:
            if not self._collection_list or self._global_cache_dir is None:
                raise ValueError(
                    "Internal error: collections not listed or global cache not setup"
                )
            yield _CollectionListUpdater(
                owner=self, collection_list=self._collection_list
            )


_COLLECTION_LIST = _CollectionListSingleton()


@contextmanager
def _update_collection_list() -> t.Iterator[_CollectionListUpdater]:
    # pylint: disable-next=protected-access
    with _COLLECTION_LIST._update_collection_list() as result:
        yield result


def get_collection_list(*, runner: Runner, global_cache_dir: Path) -> CollectionList:
    """
    Search for a list of collections. The result is cached.
    """
    _COLLECTION_LIST.setup(global_cache_dir=global_cache_dir)
    return _COLLECTION_LIST.get(runner=runner)


__all__ = [
    "CollectionList",
    "get_collection_list",
    "load_collection_data_from_disk",
]
