# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Antsibull Nox Helper.
"""

from __future__ import annotations

from .collection import CollectionSource, setup_collection_sources
from .config import load_config_from_toml
from .interpret_config import interpret_config
from .sessions import (
    ActionGroup,
    add_all_ansible_test_sanity_test_sessions,
    add_all_ansible_test_unit_test_sessions,
    add_ansible_lint,
    add_ansible_test_integration_sessions_default_container,
    add_ansible_test_sanity_test_session,
    add_ansible_test_session,
    add_ansible_test_unit_test_session,
    add_build_import_check,
    add_docs_check,
    add_extra_checks,
    add_license_check,
    add_lint_sessions,
    add_matrix_generator,
)

__version__ = "0.2.0.post0"


def setup(
    *,
    collection_sources: dict[str, str | CollectionSource] | None = None,
) -> None:
    """
    Set-up antsibull-nox.
    """
    if collection_sources:
        setup_collection_sources(
            {
                name: CollectionSource.parse(name, source)
                for name, source in collection_sources.items()
            }
        )


def load_antsibull_nox_toml() -> None:
    """
    Load and interpret antsibull-nox.toml config file.
    """
    config = load_config_from_toml("antsibull-nox.toml")
    interpret_config(config)


# pylint:disable=duplicate-code
__all__ = (
    "__version__",
    "ActionGroup",
    "add_build_import_check",
    "add_docs_check",
    "add_extra_checks",
    "add_license_check",
    "add_lint_sessions",
    "add_ansible_test_session",
    "add_ansible_test_sanity_test_session",
    "add_all_ansible_test_sanity_test_sessions",
    "add_ansible_test_unit_test_session",
    "add_all_ansible_test_unit_test_sessions",
    "add_ansible_test_integration_sessions_default_container",
    "add_ansible_lint",
    "add_matrix_generator",
    "CollectionSource",
    "setup",
    "load_antsibull_nox_toml",
)
