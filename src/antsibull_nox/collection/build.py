# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Build Ansible collections.
"""

from __future__ import annotations

from pathlib import Path

import nox

from ..paths import (
    copy_collection,
    remove_path,
)
from .data import (
    CollectionData,
)
from .search import (
    load_collection_data_from_disk,
)
from .utils import (
    force_collection_version,
)


def build_collection(
    session: nox.Session,
) -> tuple[Path | None, CollectionData, str]:
    """
    Build the current collection.

    Return a tuple (path, collection_data, version), where path might be None in case
    commands are not actually run.
    """
    tmp = Path(session.create_tmp())
    collection_dir = tmp / "collection"
    remove_path(collection_dir)
    copy_collection(Path.cwd(), collection_dir)

    collection = load_collection_data_from_disk(collection_dir, accept_manifest=False)
    version = collection.version
    if not version:
        version = "0.0.1"
        force_collection_version(collection_dir, version=version)

    with session.chdir(collection_dir):
        build_ran = session.run("ansible-galaxy", "collection", "build") is not None

    tarball = (
        collection_dir / f"{collection.namespace}-{collection.name}-{version}.tar.gz"
    )
    if build_ran and not tarball.is_file():
        files = "\n".join(
            f"* {path.name}" for path in collection_dir.iterdir() if not path.is_dir()
        )
        session.error(f"Cannot find file {tarball}! List of all files:\n{files}")

    return tarball if build_ran else None, collection, version


__all__ = [
    "build_collection",
]
