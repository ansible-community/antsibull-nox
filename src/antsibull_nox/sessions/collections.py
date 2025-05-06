# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox sessions.
"""

from __future__ import annotations

import os
import subprocess
import typing as t
from dataclasses import dataclass
from pathlib import Path

import nox

from ..ansible import AnsibleCoreVersion, parse_ansible_core_version
from ..collection import (
    CollectionData,
    setup_collections,
    setup_current_tree,
)
from ..paths import (
    create_temp_directory,
)


@dataclass
class CollectionSetup:
    """
    Information on the setup collections.
    """

    # The path of the ansible_collections directory where all dependent collections
    # are installed. Is currently identical to current_root, but that might change
    # or depend on options in the future.
    collections_root: Path

    # The directory in which ansible_collections can be found, as well as
    # ansible_collections/<namespace>/<name> points to a copy of the current collection.
    current_place: Path

    # The path of the ansible_collections directory that contains the current collection.
    # The following is always true:
    #   current_root == current_place / "ansible_collections"
    current_root: Path

    # Data on the current collection (as in the repository).
    current_collection: CollectionData

    # The path of the current collection inside the collection tree below current_root.
    # The following is always true:
    #   current_path == current_root / current_collection.namespace / current_collection.name
    current_path: Path

    def prefix_current_paths(self, paths: list[str]) -> list[str]:
        """
        Prefix the list of given paths with ``current_path``.
        """
        result = []
        for path in paths:
            prefixed_path = (self.current_path / path).relative_to(self.current_place)
            if prefixed_path.exists():
                result.append(str(prefixed_path))
        return result


def _run_subprocess(args: list[str]) -> tuple[bytes, bytes]:
    p = subprocess.run(args, check=True, capture_output=True)
    return p.stdout, p.stderr


def prepare_collections(
    session: nox.Session,
    *,
    ansible_core_version: AnsibleCoreVersion | str | None = None,
    install_in_site_packages: bool,
    extra_deps_files: list[str | os.PathLike] | None = None,
    extra_collections: list[str] | None = None,
    install_out_of_tree: bool = False,  # can not be used with install_in_site_packages=True
) -> CollectionSetup | None:
    """
    Install collections in site-packages.
    """
    parsed_ansible_core_version = (
        parse_ansible_core_version(ansible_core_version)
        if ansible_core_version is not None
        else "devel"
    )
    if install_out_of_tree and install_in_site_packages:
        raise ValueError(
            "install_out_of_tree=True cannot be combined with install_in_site_packages=True"
        )
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn("No venv. Skip preparing collections...")
        return None
    if install_in_site_packages:
        purelib = (
            session.run(
                "python",
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
                silent=True,
            )
            or ""
        ).strip()
        if not purelib:
            session.warn(
                "Cannot find site-packages (probably due to install-only run)."
                " Skip preparing collections..."
            )
            return None
        place = Path(purelib)
    elif install_out_of_tree:
        place = create_temp_directory(f"antsibull-nox-{session.name}-collection-root-")
    else:
        place = Path(session.virtualenv.location) / "collection-root"
    place.mkdir(exist_ok=True)
    setup = setup_collections(
        place,
        _run_subprocess,
        ansible_core_version=parsed_ansible_core_version,
        extra_deps_files=extra_deps_files,
        extra_collections=extra_collections,
        with_current=False,
        global_cache_dir=session.cache_dir,
    )
    current_setup = setup_current_tree(place, setup.current_collection)
    return CollectionSetup(
        collections_root=setup.root,
        current_place=place,
        current_root=current_setup.root,
        current_collection=setup.current_collection,
        current_path=t.cast(Path, current_setup.current_path),
    )


__all__ = [
    "CollectionSetup",
    "prepare_collections",
]
