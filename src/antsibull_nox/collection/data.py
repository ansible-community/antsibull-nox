# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Data types for collections.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path


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

    @classmethod
    def create(
        cls,
        *,
        collections_root_path: Path | None = None,
        path: Path,
        full_name: str,
        version: str | None = None,
        dependencies: dict[str, str] | None = None,
        current: bool = False,
    ):
        """
        Create a CollectionData object.
        """
        namespace, name = full_name.split(".", 1)
        return CollectionData(
            collections_root_path=collections_root_path,
            path=path,
            namespace=namespace,
            name=name,
            full_name=full_name,
            version=version,
            dependencies=dependencies or {},
            current=current,
        )


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


@dataclass
class CollectionSource:
    """
    Collection installation source.
    """

    # The collection's name
    name: str

    # The collection's installation source (can be passed to 'ansible-galaxy collection install')
    source: str

    @staticmethod
    def parse(collection_name: str, source: str | CollectionSource) -> CollectionSource:
        """
        Parse a CollectionSource object.
        """
        if isinstance(source, str):
            return CollectionSource(name=collection_name, source=source)

        if source.name != collection_name:
            raise ValueError(
                f"Collection name should be {collection_name!r}, but is {source.name!r}"
            )
        return source

    def identifier(self) -> str:
        """
        Compute a source identifier.
        """
        hasher = hashlib.sha256()
        hasher.update(self.name.encode("utf-8"))
        hasher.update(b"::")
        hasher.update(self.source.encode("utf-8"))
        return base64.b32encode(hasher.digest())[:16].decode("ascii")


__all__ = [
    "CollectionData",
    "SetupResult",
    "CollectionSource",
]
