# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Handle Ansible collections.
"""

from __future__ import annotations

import functools
import json
import os
import shutil
import subprocess
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from antsibull_fileutils.copier import Copier, GitCopier
from antsibull_fileutils.vcs import detect_vcs
from antsibull_fileutils.yaml import load_yaml_file


@dataclass
class CollectionData:  # pylint: disable=too-many-instance-attributes
    """
    An Ansible collection.
    """

    collections_root_path: Path | None
    path: Path
    namespace: str
    name: str
    full_name: str
    version: str | None
    dependencies: dict[str, str]
    current: bool


def _load_collection_data_from_disk(
    path: Path,
    *,
    namespace: str | None = None,
    name: str | None = None,
    root: Path | None = None,
    current: bool = False,
) -> CollectionData:
    galaxy_yml = path / "galaxy.yml"
    manifest_json = path / "MANIFEST.json"
    found: Path
    if galaxy_yml.is_file():
        found = galaxy_yml
        data = load_yaml_file(galaxy_yml)
        ns = data["namespace"]
        n = data["name"]
        v = data.get("version")
        d = data.get("dependencies")
    elif manifest_json.is_file():
        found = manifest_json
        with open(manifest_json, "br") as f:
            data = f.read()
        ci = data["collection_info"]
        ns = ci["namespace"]
        n = ci["name"]
        v = ci.get("version")
        d = ci.get("dependencies")
    else:
        raise ValueError(f"Cannot find galaxy.yml or MANIFEST.json in {path}")

    if not isinstance(ns, str):
        raise ValueError(f"{found} does not contain a namespace")
    if not isinstance(n, str):
        raise ValueError(f"{found} does not contain a name")
    if not isinstance(v, str):
        v = None
    d = d or {}
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


def _fs_list_local_collections() -> Iterator[CollectionData]:
    root: Path | None = None

    # Determine potential root
    cwd = Path.cwd()
    parents: Sequence[Path] = cwd.parents
    if len(parents) > 3 and parents[2].name == "ansible_collections":
        root = parents[3]

    # Current collection
    try:
        current = _load_collection_data_from_disk(cwd, root=root, current=True)
        if (
            root
            and current.namespace == parents[1].name
            and current.name == parents[0].name
        ):
            yield current
        else:
            root = None
            current = _load_collection_data_from_disk(cwd, current=True)
            yield current
    except Exception as exc:
        raise ValueError(
            f"Cannot load current collection's info from {cwd}: {exc}"
        ) from exc

    # Search tree
    if root:  # pylint: disable=too-many-nested-blocks
        for namespace in root.iterdir():
            try:
                if namespace.is_dir() or namespace.is_symlink():
                    for name in namespace.iterdir():
                        try:
                            if name.is_dir() or name.is_symlink():
                                yield _load_collection_data_from_disk(
                                    name,
                                    namespace=namespace.name,
                                    name=name.name,
                                    root=root,
                                )
                        except Exception:  # pylint: disable=broad-exception-caught
                            # If name doesn't happen to be a (symlink to a) directory, ...
                            pass
            except Exception:  # pylint: disable=broad-exception-caught
                # If namespace doesn't happen to be a (symlink to a) directory, ...
                pass


def _galaxy_list_collections() -> Iterator[CollectionData]:
    try:
        p = subprocess.run(
            ["ansible-galaxy", "collection", "list", "--format", "json"],
            check=True,
            capture_output=True,
        )
        data = json.loads(p.stdout)
        for collections_root_path, collections in data.items():
            root = Path(collections_root_path)
            for collection in collections:
                namespace, name = collection.split(".", 1)
                try:
                    yield _load_collection_data_from_disk(
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

    @staticmethod
    def collect() -> CollectionList:
        """
        Search for a list of collections. The result is not cached.
        """

        found_collections = {}
        for collection_data in _fs_list_local_collections():
            found_collections[collection_data.full_name] = collection_data
        for collection_data in _galaxy_list_collections():
            # Similar to Ansible, we use the first match
            if collection_data.full_name not in found_collections:
                found_collections[collection_data.full_name] = collection_data
        collections = sorted(found_collections.values(), key=lambda cli: cli.full_name)
        current = next(c for c in collections if c.current)
        return CollectionList(
            collections=collections,
            collection_map=found_collections,
            current=current,
        )

    def find(self, name: str) -> CollectionData | None:
        """
        Find a collection for a given name.
        """
        return self.collection_map.get(name)


@functools.cache
def get_collection_list() -> CollectionList:
    """
    Search for a list of collections. The result is cached.
    """
    return CollectionList.collect()


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


def _remove(path: Path) -> None:
    if not path.is_symlink() and path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


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
                if not isinstance(data, dict):
                    raise ValueError(
                        f"Collection entry #{index + 1} must be a string or dictionary"
                    )
                if not isinstance(data.get("name"), str):
                    raise ValueError(
                        f"Collection entry #{index + 1} does not have a 'name' field of type string"
                    )
                result.append(data["name"])
        return result
    except Exception as exc:
        raise ValueError(
            f"Error while loading collection dependency file {path}: {exc}"
        ) from exc


@dataclass
class SetupResult:
    """
    Information on how the collections are set up.
    """

    # The path of the ansible_collections directory.
    root: Path

    # Data on the current collection (as in the repository).
    current_collection: CollectionData

    # If it was installed, the path of the current collection inside the collection tree below root.
    current_path: Path | None


def setup_collections(
    destination: str | os.PathLike,
    *,
    extra_deps_files: list[str | os.PathLike] | None = None,
    with_current: bool = True,
) -> SetupResult:
    """
    Setup all collections in a tree structure inside the destination directory.
    """
    all_collections = get_collection_list()
    destination_root = Path(destination) / "ansible_collections"
    destination_root.mkdir(exist_ok=True)
    current = all_collections.current
    collections_to_install = {current.full_name: current}
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
    if path.exists():
        _remove(path)
    vcs = detect_vcs(collection.path)
    copier = {
        "none": Copier,
        "git": GitCopier,
    }.get(vcs, Copier)()
    copier.copy(collection.path, path, exclude_root=[".nox", ".tox"])


def _copy_collection_rsync_hard_links(collection: CollectionData, path: Path) -> None:
    subprocess.run(
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
        ],
        check=True,
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
    # _copy_collection_rsync_hard_links(current_collection, collection)
    return SetupResult(
        root=root,
        current_collection=current_collection,
        current_path=collection,
    )


__all__ = [
    "CollectionData",
    "CollectionList",
    "SetupResult",
    "get_collection_list",
    "setup_collections",
    "setup_current_tree",
]
