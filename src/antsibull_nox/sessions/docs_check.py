# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox docs check session.
"""

from __future__ import annotations

import typing as t

import nox

from .collections import (
    CollectionSetup,
    prepare_collections,
)
from .utils import install


def add_docs_check(
    *,
    make_docs_check_default: bool = True,
    antsibull_docs_package: str = "antsibull-docs",
    ansible_core_package: str = "ansible-core",
    validate_collection_refs: t.Literal["self", "dependent", "all"] | None = None,
    extra_collections: list[str] | None = None,
) -> None:
    """
    Add docs-check session for linting.
    """

    def compose_dependencies() -> list[str]:
        deps = [antsibull_docs_package, ansible_core_package]
        return deps

    def execute_antsibull_docs(
        session: nox.Session, prepared_collections: CollectionSetup
    ) -> None:
        with session.chdir(prepared_collections.current_path):
            collections_path = f"{prepared_collections.current_place}"
            command = [
                "antsibull-docs",
                "lint-collection-docs",
                "--plugin-docs",
                "--skip-rstcheck",
                ".",
            ]
            if validate_collection_refs:
                command.extend(["--validate-collection-refs", validate_collection_refs])
            session.run(*command, env={"ANSIBLE_COLLECTIONS_PATH": collections_path})

    def docs_check(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        prepared_collections = prepare_collections(
            session,
            install_in_site_packages=False,
            extra_collections=extra_collections,
            install_out_of_tree=True,
        )
        if not prepared_collections:
            session.warn("Skipping antsibull-docs...")
        if prepared_collections:
            execute_antsibull_docs(session, prepared_collections)

    docs_check.__doc__ = "Run 'antsibull-docs lint-collection-docs'"
    nox.session(
        name="docs-check",
        default=make_docs_check_default,
    )(docs_check)


__all__ = [
    "add_docs_check",
]
