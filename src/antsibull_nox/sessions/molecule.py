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

import nox

from .collections import prepare_collections
from .utils.packages import (
    PackageType,
    PackageTypeOrList,
    check_package_types,
    install,
    normalize_package_type,
)


def add_molecule(
    *,
    default: bool = False,
    molecule_package: PackageTypeOrList = "molecule",
    additional_requirements_files: Sequence[str | os.PathLike] | None = None,
    debug: bool = False,
    all: bool = False,
    scenarios: list[str] = [],
    exclude_scenarios: list[str] = [],
    parallel: bool = False,
    shared_state: bool = False
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
        install(session, *compose_dependencies(session))
        # TODO: Support globbing for molecule convention of
        # extensions/molecule/<scenario>/requirements.yml
        extra_deps_files: list[str | os.PathLike] = [
            "requirements.yml",
            # Taken from
            # https://github.com/ansible/molecule/blob/main/docs/getting-started-collections.md
            "extensions/molecule/requirements.yml",
            # Taken from
            # https://github.com/ansible/molecule/blob/main/docs/getting-started-playbooks.md?plain=1#L49
            "molecule/requirements.yml"
        ]
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
        # TODO: Detect if extensions/molecule exists and change directory
        # If it does not exist, stay where we are and verify the molecule directory
        # exists
        command = ["molecule", "test"]
        if debug:
            command.insert(1, "--debug")
        if all:
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
