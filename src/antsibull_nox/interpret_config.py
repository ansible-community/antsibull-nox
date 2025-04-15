# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Interpret config.
"""

from __future__ import annotations

from .collection import CollectionSource, setup_collection_sources
from .config import ActionGroup as ConfigActionGroup
from .config import CollectionSource as ConfigCollectionSource
from .config import (
    Config,
    DevelLikeBranch,
    SessionAnsibleLint,
    SessionAnsibleTestIntegrationWDefaultContainer,
    SessionAnsibleTestSanity,
    SessionAnsibleTestUnits,
    SessionBuildImportCheck,
    SessionDocsCheck,
    SessionExtraChecks,
    SessionLicenseCheck,
    SessionLint,
    Sessions,
)
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


def _interpret_config(config: Config) -> None:
    if config.collection_sources:
        ...


def _add_sessions(config: Config) -> None:
    # TODO
    add_matrix_generator()


def interpret_config(config: Config) -> None:
    _interpret_config(config)
    _add_sessions(config)
