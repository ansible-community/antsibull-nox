# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox ansible-lint session.
"""

from __future__ import annotations

import nox

from .collections import prepare_collections
from .utils import install


def add_ansible_lint(
    *,
    make_ansible_lint_default: bool = True,
    ansible_lint_package: str = "ansible-lint",
    strict: bool = False,
) -> None:
    """
    Add a session that runs ansible-lint.
    """

    def compose_dependencies() -> list[str]:
        return [ansible_lint_package]

    def ansible_lint(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        prepared_collections = prepare_collections(
            session,
            install_in_site_packages=False,
            install_out_of_tree=True,
            extra_deps_files=["tests/integration/requirements.yml"],
        )
        if not prepared_collections:
            session.warn("Skipping ansible-lint...")
            return
        env = {"ANSIBLE_COLLECTIONS_PATH": f"{prepared_collections.current_place}"}
        command = ["ansible-lint", "--offline"]
        if strict:
            command.append("--strict")
        if session.posargs:
            command.extend(session.posargs)
        session.run(*command, env=env)

    ansible_lint.__doc__ = "Run ansible-lint."
    nox.session(
        name="ansible-lint",
        default=make_ansible_lint_default,
    )(ansible_lint)


__all__ = [
    "add_ansible_lint",
]
