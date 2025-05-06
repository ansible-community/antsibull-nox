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
import shutil
import tempfile
import typing as t
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from antsibull_fileutils.yaml import load_yaml_file

from ..ansible import AnsibleCoreVersion
from ..paths import copy_collection as _paths_copy_collection
from ..paths import remove_path as _remove
from .data import CollectionData, CollectionSource, SetupResult
from .extract import extract_tarball
from .search import (
    CollectionList,
    _update_collection_list,
    get_collection_list,
)

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

    @t.overload
    def get_source(
        self, name: str, *, create_default: t.Literal[True] = True
    ) -> CollectionSource: ...

    @t.overload
    def get_source(
        self, name: str, *, create_default: t.Literal[False]
    ) -> CollectionSource | None: ...

    def get_source(
        self, name: str, *, create_default: bool = True
    ) -> CollectionSource | None:
        """
        Get source for collection.
        """
        source = self.sources.get(name)
        if source is None and create_default:
            source = CollectionSource(name, name)
        return source


class _CollectionDownloadCache:
    @staticmethod
    def _parse_galaxy_filename(file: Path) -> tuple[str, str, str]:
        """
        Split filename into (namespace, name, version) tuple.
        """
        if not file.name.endswith(_TARBALL_EXTENSION):
            raise ValueError(
                f"Filename {file.name!r} does not end with {_TARBALL_EXTENSION}"
            )
        parts = file.name[: -len(_TARBALL_EXTENSION)].split("-", 2)
        if len(parts) != 3:
            raise ValueError(
                f"Filename {file.name!r} does not belong to a Galaxy tarball"
            )
        return parts[0], parts[1], parts[2]

    @staticmethod
    def _parse_cache_filename(file: Path) -> tuple[str, str, str, str] | None:
        """
        Split cache filename into (namespace, name, source_id, version) tuple.
        """
        if not file.name.endswith(_TARBALL_EXTENSION):
            return None
        parts = file.name[: -len(_TARBALL_EXTENSION)].split("-", 3)
        if len(parts) != 4:
            return None
        return parts[0], parts[1], parts[2], parts[3]

    @staticmethod
    def _encode_cache_filename(
        namespace: str, name: str, version: str, source: CollectionSource
    ) -> str:
        return f"{namespace}-{name}-{source.identifier()}-{version}{_TARBALL_EXTENSION}"

    def download_collections(
        self, *, destination: Path, sources: list[CollectionSource], runner: Runner
    ) -> None:
        """
        Given a set of collection sources, downloads these and stores them in destination.
        """
        destination.mkdir(exist_ok=True)
        names = ", ".join(sorted(source.name for source in sources))
        print(f"Downloading {names} to {destination}...")
        sources_by_name = {}
        for source in sources:
            sources_by_name[source.name] = source
            if source.name != source.source:
                print(f"  Installing {source.name} via {source.source}...")
        with tempfile.TemporaryDirectory(
            prefix="antsibull-nox-galaxy-download"
        ) as dest:
            tempdir = Path(dest)
            command = [
                "ansible-galaxy",
                "collection",
                "download",
                "--no-deps",
                "--download-path",
                str(tempdir),
                "--",
                *(source.source for source in sources),
            ]
            runner(command)
            for file in tempdir.iterdir():
                if file.name.endswith(_TARBALL_EXTENSION) and file.is_file():
                    namespace, name, version = self._parse_galaxy_filename(file)
                    source_opt = sources_by_name.get(f"{namespace}.{name}")
                    if source_opt is None:
                        print(
                            f"Found unknown collection artifact {file.name!r}, ignoring..."
                        )
                        continue
                    destfile = destination / self._encode_cache_filename(
                        namespace, name, version, source_opt
                    )
                    _remove(destfile)
                    shutil.move(file, destfile)

    def list_downloaded_dir(
        self, *, path: Path
    ) -> dict[tuple[str, str], tuple[Path, str]]:
        """
        List contents of download cache.

        Returns a dictionary mapping (collection_name, source_id) tuples to
        (tarball_path, version) tuples.
        """
        if not path.is_dir():
            return {}
        result: dict[tuple[str, str], tuple[Path, str]] = {}
        for file in path.iterdir():
            if not file.is_file():
                continue
            parsed = self._parse_cache_filename(file)
            if parsed is None:
                continue
            namespace, name, source_id, version = parsed
            collection_name = f"{namespace}.{name}"
            key = collection_name, source_id
            if key in result:
                # Determine older entry
                old_file = result[key][0]
                old_stat = old_file.stat()
                new_stat = file.stat()
                if new_stat.st_mtime > old_stat.st_mtime:
                    older_file = old_file
                    result[key] = file, version
                else:
                    older_file = file
                # Clean up older entry
                _remove(older_file)
            else:
                result[key] = file, version
        return result


_COLLECTION_SOURCES = _CollectionSources()
_COLLECTION_SOURCES_PER_CORE_VERSION: dict[AnsibleCoreVersion, _CollectionSources] = {}
_COLLECTION_DOWNLOAD_CACHE = _CollectionDownloadCache()
_TARBALL_EXTENSION = ".tar.gz"
_INSTALLATION_CONFIG_ENV_VAR = "ANTSIBULL_NOX_INSTALL_COLLECTIONS"


def setup_collection_sources(
    collection_sources: dict[str, CollectionSource],
    *,
    ansible_core_version: AnsibleCoreVersion | None = None,
) -> None:
    """
    Setup collection sources.
    """
    sources = _COLLECTION_SOURCES
    if ansible_core_version is not None:
        sources = _COLLECTION_SOURCES_PER_CORE_VERSION.get(
            ansible_core_version, _COLLECTION_SOURCES
        )
        if sources is _COLLECTION_SOURCES:
            sources = _CollectionSources()
            _COLLECTION_SOURCES_PER_CORE_VERSION[ansible_core_version] = sources
    for name, source in collection_sources.items():
        sources.set_source(name, source)


def _install_from_download_cache(
    *, full_name: str, tarball: Path, destination: Path
) -> Path:
    destination_dir = destination / full_name
    _remove(destination_dir)
    print(f"Installing {full_name} from {tarball} to {destination_dir}...")
    extract_tarball(tarball=tarball, destination=destination_dir)
    return destination_dir


def _get_source(
    name: str, *, ansible_core_version: AnsibleCoreVersion
) -> CollectionSource:
    sources_per_version = _COLLECTION_SOURCES_PER_CORE_VERSION.get(ansible_core_version)
    if sources_per_version:
        result = sources_per_version.get_source(name, create_default=False)
        if result is not None:
            return result
    return _COLLECTION_SOURCES.get_source(name)


def _install_missing(
    collections: list[str],
    *,
    ansible_core_version: AnsibleCoreVersion,
    runner: Runner,
) -> list[CollectionData]:
    config = os.environ.get(_INSTALLATION_CONFIG_ENV_VAR)
    if config == "never":
        names = ", ".join(sorted(collections))
        plural_s = "" if len(collections) == 1 else "s"
        print(
            f"{_INSTALLATION_CONFIG_ENV_VAR} is set to 'never',"
            f" thus cannot install missing exception{plural_s} {names}..."
        )
        return []
    sources = [
        _get_source(name, ansible_core_version=ansible_core_version)
        for name in collections
    ]
    result: list[CollectionData] = []
    with _update_collection_list(ansible_core_version=ansible_core_version) as updater:
        global_cache = updater.get_global_cache()
        install: list[CollectionSource] = []
        download: list[CollectionSource] = []
        download_cache = _COLLECTION_DOWNLOAD_CACHE.list_downloaded_dir(
            path=global_cache.download_cache
        )
        for source in sources:
            if cd := updater.find(source.name):
                result.append(cd)
            else:
                install.append(source)
                if not download_cache.get((source.name, source.identifier())):
                    download.append(source)
        if download:
            _COLLECTION_DOWNLOAD_CACHE.download_collections(
                destination=global_cache.download_cache, sources=download, runner=runner
            )
            download_cache = _COLLECTION_DOWNLOAD_CACHE.list_downloaded_dir(
                path=global_cache.download_cache
            )
        if install:
            for source in install:
                key = source.name, source.identifier()
                if key not in download_cache:
                    raise ValueError(
                        f"Error: cannot find {source.name} (source ID {source.identifier()})"
                        f" in download cache {global_cache.download_cache}"
                        " after successful download!"
                    )
                c_dir = _install_from_download_cache(
                    full_name=source.name,
                    tarball=download_cache[key][0],
                    destination=global_cache.get_extracted_path(
                        ansible_core_version=ansible_core_version
                    ),
                )
                c_namespace, c_name = source.name.split(".", 1)
                result.append(
                    updater.add_collection(
                        directory=c_dir, namespace=c_namespace, name=c_name
                    )
                )
    return result


@dataclass(frozen=True, order=True)
class _Source:
    """
    Represents the source of a missing dependency.
    """

    name: str | None = None
    path: Path | None = None
    what: str | None = None

    @classmethod
    def dependency_of(cls, name: str) -> _Source:
        """
        Dependency of collection.
        """
        return cls(name=name)

    @classmethod
    def from_file(cls, path: Path) -> _Source:
        """
        Dependency from collection requirements file.
        """
        return cls(path=path)

    @classmethod
    def from_other(cls, what: str) -> _Source:
        """
        Another source.
        """
        return cls(what=what)

    def nice_str(self) -> str:
        """
        Convert to a nice (human readable) string.
        """
        if self.name:
            return f"dependency of {self.name}"
        if self.path:
            return f"required in {self.path}"
        if self.what:
            return f"required through {self.what}"
        return "(unknown)"


class _MissingDependency:
    """
    Models a missing dependency with a list of sources where it is required from.
    """

    name: str
    sources: set[_Source]

    def __init__(self, name: str, source: _Source) -> None:
        """
        Create missing dependency with source.
        """
        self.name = name
        self.sources = {source}

    def add_source(self, source: _Source) -> None:
        """
        Add source.
        """
        self.sources.add(source)


class _MissingDependencies:
    """
    Models all missing dependencies.
    """

    missing: dict[str, _MissingDependency]

    def __init__(self) -> None:
        self.missing = {}

    def is_empty(self) -> bool:
        """
        Query whether no collections are missing.
        """
        return not self.missing

    def get_missing_names(self) -> list[str]:
        """
        Get a sorted list of missing collections.
        """
        return sorted(self.missing)

    def add(self, name: str, *, source: _Source) -> None:
        """
        Add a missing dependency.
        """
        if name in self.missing:
            self.missing[name].add_source(source)
        else:
            self.missing[name] = _MissingDependency(name, source)

    def remove(self, name: str) -> None:
        """
        Remove a missing dependency (because it was installed).
        """
        self.missing.pop(name)

    def raise_error(self) -> None:
        """
        Raise a human-readable error about missing collections.
        If no collections are missing, simply return.
        """
        if not self.missing:
            return
        collections: list[str] = []
        for collection in sorted(self.missing):
            sources = sorted(self.missing[collection].sources)
            sources_text = ", ".join(source.nice_str() for source in sources)
            collections.append(f"{collection}  (required from {sources_text})")
        plural_s = "" if len(collections) == 1 else ""
        enumeration = "- " + "\n- ".join(collections)
        raise ValueError(
            f"The following collection{plural_s} are missing:\n{enumeration}"
        )


def _add_all_dependencies(
    collections: dict[str, CollectionData],
    missing_dependencies: _MissingDependencies,
    all_collections: CollectionList,
) -> None:
    to_process = list(collections.values())
    while to_process:
        collection = to_process.pop(0)
        for dependency_name in collection.dependencies:
            if dependency_name not in collections:
                dependency_data = all_collections.find(dependency_name)
                if dependency_data is None:
                    missing_dependencies.add(
                        dependency_name,
                        source=_Source.dependency_of(collection.full_name),
                    )
                    continue
                collections[dependency_name] = dependency_data
                to_process.append(dependency_data)


def _install_collection(collection: CollectionData, path: Path) -> None:
    # Compute relative path
    sym_path = collection.path.absolute().relative_to(path.parents[0], walk_up=True)
    # Ensure that path is symlink with this relative path
    if path.is_symlink():
        if path.readlink() == sym_path:
            return
        path.unlink()
    else:
        _remove(path)
    path.symlink_to(sym_path)


def _install_current_collection(collection: CollectionData, path: Path) -> None:
    if path.exists() and (path.is_symlink() or not path.is_dir()):
        path.unlink()
    path.mkdir(exist_ok=True)
    present = {p.name for p in path.iterdir()}
    for source_entry in collection.path.absolute().iterdir():
        if source_entry.name == ".nox":
            continue
        dest_entry = path / source_entry.name
        # Compute relative path
        sym_path = source_entry.relative_to(path, walk_up=True)
        # Ensure that dest_entry is symlink with this relative path
        if source_entry.name in present:
            present.remove(source_entry.name)
            if dest_entry.is_symlink() and dest_entry.readlink() == sym_path:
                continue
            _remove(dest_entry)
        dest_entry.symlink_to(sym_path)
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
    ansible_core_version: AnsibleCoreVersion,
    extra_collections: list[str] | None = None,
    extra_deps_files: list[str | os.PathLike] | None = None,
    global_cache_dir: Path,
    with_current: bool = True,
) -> SetupResult:
    """
    Setup all collections in a tree structure inside the destination directory.
    """
    all_collections = get_collection_list(
        runner=runner,
        global_cache_dir=global_cache_dir,
        ansible_core_version=ansible_core_version,
    )
    destination_root = Path(destination) / "ansible_collections"
    destination_root.mkdir(exist_ok=True)
    current = all_collections.current
    collections_to_install = {current.full_name: current}
    missing = _MissingDependencies()
    if extra_collections:
        for collection in extra_collections:
            collection_data = all_collections.find(collection)
            if collection_data is None:
                missing.add(collection, source=_Source.from_other("noxfile"))
            else:
                collections_to_install[collection_data.full_name] = collection_data
    if extra_deps_files is not None:
        for extra_deps_file in extra_deps_files:
            path = Path(extra_deps_file)
            for collection in _extract_collections_from_extra_deps_file(path):
                collection_data = all_collections.find(collection)
                if collection_data is None:
                    missing.add(collection, source=_Source.from_file(path))
                else:
                    collections_to_install[collection_data.full_name] = collection_data
    while True:
        _add_all_dependencies(collections_to_install, missing, all_collections)
        if missing.is_empty():
            break
        for collection_data in _install_missing(
            missing.get_missing_names(),
            ansible_core_version=ansible_core_version,
            runner=runner,
        ):
            collections_to_install[collection_data.full_name] = collection_data
            missing.remove(collection_data.full_name)
        missing.raise_error()
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
