# Author: Daniel Brennand <contact@danielbrennand.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Create nox molecule session.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import nox

from ..paths.utils import list_all_files
from .collections import prepare_collections
from .utils.packages import (
    PackageType,
    PackageTypeOrList,
    check_package_types,
    install,
    normalize_package_type,
)

# Taken from:
# https://github.com/ansible/molecule/blob/main/src/molecule/constants.py#L26
_MOLECULE_COLLECTION_ROOT: str = "extensions/molecule"
_MOLECULE_COLLECTION_REQUIREMENTS_GLOB: str = (
    f"{_MOLECULE_COLLECTION_ROOT}/*/requirements.yml"
)


def check_molecule_collection_root() -> bool:
    """
    Determine whether the molecule collection root exists.
    """
    cwd: Path = Path.cwd()
    molecule_collection_root_dir: Path = cwd / _MOLECULE_COLLECTION_ROOT
    if molecule_collection_root_dir.exists():
        return True
    return False


def find_molecule_scenario_requirements() -> list[Path]:
    """
    Find requirements.yml files located in molecule scenario directories.

    Reference documentation:
    https://github.com/ansible/molecule/blob/main/src/molecule/dependency/ansible_galaxy/roles.py#L41
    """
    requirements_files: list[Path] = []
    for path in list_all_files():
        if path.match(_MOLECULE_COLLECTION_REQUIREMENTS_GLOB):
            requirements_files.append(path)
    return requirements_files


def add_molecule(
    *,
    default: bool = False,
    molecule_package: PackageTypeOrList = "molecule",
    additional_requirements_files: Sequence[str | os.PathLike] | None = None,
    debug: bool = False,
    run_all: bool = False,
    scenarios: list[str] = [],
    exclude_scenarios: list[str] = [],
    parallel: bool = False,
    shared_state: bool = False,
) -> None:
    """
    Add a session that runs molecule.
    """

    def compose_dependencies(session: nox.Session) -> list[PackageType]:
        return check_package_types(
            session,
            "sessions.molecule.molecule_package",
            normalize_package_type(molecule_package),
        )

    def molecule(session: nox.Session) -> None:
        molecule_collection_root_exists: bool = check_molecule_collection_root()
        if not molecule_collection_root_exists:
            # Warn users to migrate to the new molecule collection root directory
            # https://github.com/ansible/molecule/blob/main/src/molecule/util.py#L651
            session.warn(
                f"Molecule collection root directory {_MOLECULE_COLLECTION_ROOT} was not found."
                f" Molecule scenarios should be migrated to {_MOLECULE_COLLECTION_ROOT}."
                " We will attempt to use 'molecule' directory at the collection root."
            )
        install(session, *compose_dependencies(session))
        extra_deps_files: list[str | os.PathLike] = [
            "requirements.yml",
            # Taken from
            # https://github.com/ansible/molecule/blob/main/docs/getting-started-playbooks.md?plain=1#L49
            "molecule/requirements.yml",
            # Taken from
            # https://github.com/ansible/molecule/blob/main/docs/getting-started-collections.md
            "extensions/molecule/requirements.yml",
        ]
        discovered_molecule_requirements_files = find_molecule_scenario_requirements()
        if discovered_molecule_requirements_files:
            extra_deps_files.extend(discovered_molecule_requirements_files)
        if additional_requirements_files:
            extra_deps_files.extend(additional_requirements_files)
        prepared_collections = prepare_collections(
            session,
            install_in_site_packages=False,
            install_out_of_tree=True,
            extra_deps_files=extra_deps_files,
        )
        if not prepared_collections:
            session.warn("Skipping molecule...")
            return
        env = {"ANSIBLE_COLLECTIONS_PATH": f"{prepared_collections.current_place}"}
        command = ["molecule", "test"]
        if debug:
            command.insert(1, "--debug")
        if run_all:
            command.append("--all")
        if parallel:
            command.append("--parallel")
        if scenarios:
            for scenario in scenarios:
                command.append(f"--scenario-name {scenario}")
        if exclude_scenarios:
            for scenario in exclude_scenarios:
                command.append(f"--exclude {scenario}")
        if shared_state:
            command.append("--shared-state")
        if molecule_collection_root_exists:
            # Ensure we are in _MOLECULE_COLLECTION_ROOT prior to running molecule test
            command = ["cd", "extensions/molecule", "&&", *command]
        if session.posargs:
            command.extend(session.posargs)
        session.run(*command, env=env)

    molecule.__doc__ = "Run molecule."
    nox.session(
        name="molecule",
        default=default,
    )(molecule)


__all__ = [
    "add_molecule",
]
