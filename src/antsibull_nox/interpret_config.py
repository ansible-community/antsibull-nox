# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Interpret config.
"""

from __future__ import annotations

import typing as t

from .ansible import AnsibleCoreVersion
from .collection import CollectionSource, setup_collection_sources
from .config import ActionGroup as ConfigActionGroup
from .config import (
    Config,
    DevelLikeBranch,
    Sessions,
)
from .sessions import add_matrix_generator
from .sessions.ansible_lint import add_ansible_lint
from .sessions.ansible_test import (
    add_all_ansible_test_sanity_test_sessions,
    add_all_ansible_test_unit_test_sessions,
    add_ansible_test_integration_sessions_default_container,
)
from .sessions.build_import_check import add_build_import_check
from .sessions.docs_check import add_docs_check
from .sessions.extra_checks import (
    ActionGroup,
    add_extra_checks,
)
from .sessions.license_check import add_license_check
from .sessions.lint import add_lint_sessions
from .utils import Version


def _interpret_config(config: Config) -> None:
    if config.collection_sources:
        setup_collection_sources(
            {
                name: CollectionSource(name=name, source=source.source)
                for name, source in config.collection_sources.items()
            }
        )
    if config.collection_sources_per_ansible:
        for (
            ansible_core_version,
            collection_sources,
        ) in config.collection_sources_per_ansible.items():
            setup_collection_sources(
                {
                    name: CollectionSource(name=name, source=source.source)
                    for name, source in collection_sources.items()
                },
                ansible_core_version=ansible_core_version,
            )


def _convert_action_groups(
    action_groups: list[ConfigActionGroup] | None,
) -> list[ActionGroup] | None:
    if action_groups is None:
        return None
    return [
        ActionGroup(
            name=action_group.name,
            pattern=action_group.pattern,
            doc_fragment=action_group.doc_fragment,
            exclusions=action_group.exclusions,
        )
        for action_group in action_groups
    ]


def _convert_devel_like_branches(
    devel_like_branches: list[DevelLikeBranch] | None,
) -> list[tuple[str | None, str]] | None:
    if devel_like_branches is None:
        return None
    return [(branch.repository, branch.branch) for branch in devel_like_branches]


def _convert_except_versions(
    except_versions: list[AnsibleCoreVersion] | None,
) -> list[AnsibleCoreVersion | str] | None:
    return t.cast(t.Optional[list[AnsibleCoreVersion | str]], except_versions)


def _convert_core_python_versions(
    core_python_versions: dict[AnsibleCoreVersion | str, list[Version]] | None,
) -> dict[str | AnsibleCoreVersion, list[str | Version]] | None:
    return t.cast(
        t.Optional[dict[str | AnsibleCoreVersion, list[str | Version]]],
        core_python_versions,
    )


def _add_sessions(sessions: Sessions) -> None:
    if sessions.lint:
        add_lint_sessions(
            make_lint_default=sessions.lint.default,
            extra_code_files=sessions.lint.extra_code_files,
            run_isort=sessions.lint.run_isort,
            isort_config=sessions.lint.isort_config,
            isort_package=sessions.lint.isort_package,
            run_black=sessions.lint.run_black,
            run_black_modules=sessions.lint.run_black_modules,
            black_config=sessions.lint.black_config,
            black_package=sessions.lint.black_package,
            run_ruff_format=sessions.lint.run_ruff_format,
            ruff_format_config=sessions.lint.ruff_format_config
            or sessions.lint.ruff_config,
            ruff_format_package=sessions.lint.ruff_format_package
            or sessions.lint.ruff_package,
            run_ruff_autofix=sessions.lint.run_ruff_autofix,
            ruff_autofix_config=sessions.lint.ruff_autofix_config
            or sessions.lint.ruff_config,
            ruff_autofix_package=sessions.lint.ruff_autofix_package
            or sessions.lint.ruff_package,
            ruff_autofix_select=sessions.lint.ruff_autofix_select,
            run_ruff_check=sessions.lint.run_ruff_check,
            ruff_check_config=sessions.lint.ruff_check_config
            or sessions.lint.ruff_config,
            ruff_check_package=sessions.lint.ruff_check_package
            or sessions.lint.ruff_package,
            run_flake8=sessions.lint.run_flake8,
            flake8_config=sessions.lint.flake8_config,
            flake8_package=sessions.lint.flake8_package,
            run_pylint=sessions.lint.run_pylint,
            pylint_rcfile=sessions.lint.pylint_rcfile,
            pylint_modules_rcfile=sessions.lint.pylint_modules_rcfile,
            pylint_package=sessions.lint.pylint_package,
            pylint_ansible_core_package=sessions.lint.pylint_ansible_core_package,
            pylint_extra_deps=sessions.lint.pylint_extra_deps,
            run_yamllint=sessions.lint.run_yamllint,
            yamllint_config=sessions.lint.yamllint_config,
            yamllint_config_plugins=sessions.lint.yamllint_config_plugins,
            yamllint_config_plugins_examples=sessions.lint.yamllint_config_plugins_examples,
            yamllint_config_extra_docs=sessions.lint.yamllint_config_extra_docs,
            yamllint_package=sessions.lint.yamllint_package,
            yamllint_antsibull_docutils_package=sessions.lint.yamllint_antsibull_docutils_package,
            run_mypy=sessions.lint.run_mypy,
            mypy_config=sessions.lint.mypy_config,
            mypy_package=sessions.lint.mypy_package,
            mypy_ansible_core_package=sessions.lint.mypy_ansible_core_package,
            mypy_extra_deps=sessions.lint.mypy_extra_deps,
            run_antsibullnox_config_lint=sessions.lint.run_antsibullnox_config_lint,
        )
    if sessions.docs_check:
        add_docs_check(
            make_docs_check_default=sessions.docs_check.default,
            antsibull_docs_package=sessions.docs_check.antsibull_docs_package,
            ansible_core_package=sessions.docs_check.ansible_core_package,
            validate_collection_refs=sessions.docs_check.validate_collection_refs,
            extra_collections=sessions.docs_check.extra_collections,
            codeblocks_restrict_types=sessions.docs_check.codeblocks_restrict_types,
            codeblocks_restrict_type_exact_case=(
                sessions.docs_check.codeblocks_restrict_type_exact_case
            ),
            codeblocks_allow_without_type=sessions.docs_check.codeblocks_allow_without_type,
            codeblocks_allow_literal_blocks=sessions.docs_check.codeblocks_allow_literal_blocks,
            antsibull_docutils_package=sessions.docs_check.antsibull_docutils_package,
        )
    if sessions.license_check:
        add_license_check(
            make_license_check_default=sessions.license_check.default,
            run_reuse=sessions.license_check.run_reuse,
            reuse_package=sessions.license_check.reuse_package,
            run_license_check=sessions.license_check.run_license_check,
            license_check_extra_ignore_paths=(
                sessions.license_check.license_check_extra_ignore_paths
            ),
        )
    if sessions.extra_checks:
        add_extra_checks(
            make_extra_checks_default=sessions.extra_checks.default,
            run_no_unwanted_files=sessions.extra_checks.run_no_unwanted_files,
            no_unwanted_files_module_extensions=(
                sessions.extra_checks.no_unwanted_files_module_extensions
            ),
            no_unwanted_files_other_extensions=(
                sessions.extra_checks.no_unwanted_files_other_extensions
            ),
            no_unwanted_files_yaml_extensions=(
                sessions.extra_checks.no_unwanted_files_yaml_extensions
            ),
            no_unwanted_files_skip_paths=(
                sessions.extra_checks.no_unwanted_files_skip_paths
            ),
            no_unwanted_files_skip_directories=(
                sessions.extra_checks.no_unwanted_files_skip_directories
            ),
            no_unwanted_files_yaml_directories=(
                sessions.extra_checks.no_unwanted_files_yaml_directories
            ),
            no_unwanted_files_allow_symlinks=(
                sessions.extra_checks.no_unwanted_files_allow_symlinks
            ),
            run_action_groups=sessions.extra_checks.run_action_groups,
            action_groups_config=_convert_action_groups(
                sessions.extra_checks.action_groups_config
            ),
            run_no_trailing_whitespace=sessions.extra_checks.run_no_trailing_whitespace,
            no_trailing_whitespace_skip_paths=(
                sessions.extra_checks.no_trailing_whitespace_skip_paths
            ),
            no_trailing_whitespace_skip_directories=(
                sessions.extra_checks.no_trailing_whitespace_skip_directories
            ),
        )
    if sessions.build_import_check:
        add_build_import_check(
            make_build_import_check_default=sessions.build_import_check.default,
            ansible_core_package=sessions.build_import_check.ansible_core_package,
            run_galaxy_importer=sessions.build_import_check.run_galaxy_importer,
            galaxy_importer_package=sessions.build_import_check.galaxy_importer_package,
            galaxy_importer_config_path=sessions.build_import_check.galaxy_importer_config_path,
            galaxy_importer_always_show_logs=(
                sessions.build_import_check.galaxy_importer_always_show_logs
            ),
        )
    if sessions.ansible_test_sanity:
        add_all_ansible_test_sanity_test_sessions(
            default=sessions.ansible_test_sanity.default,
            include_devel=sessions.ansible_test_sanity.include_devel,
            include_milestone=sessions.ansible_test_sanity.include_milestone,
            add_devel_like_branches=_convert_devel_like_branches(
                sessions.ansible_test_sanity.add_devel_like_branches
            ),
            min_version=sessions.ansible_test_sanity.min_version,
            max_version=sessions.ansible_test_sanity.max_version,
            except_versions=_convert_except_versions(
                sessions.ansible_test_sanity.except_versions
            ),
            skip_tests=sessions.ansible_test_sanity.skip_tests,
            allow_disabled=sessions.ansible_test_sanity.allow_disabled,
            enable_optional_errors=sessions.ansible_test_sanity.enable_optional_errors,
        )
    if sessions.ansible_test_units:
        add_all_ansible_test_unit_test_sessions(
            default=sessions.ansible_test_units.default,
            include_devel=sessions.ansible_test_units.include_devel,
            include_milestone=sessions.ansible_test_units.include_milestone,
            add_devel_like_branches=_convert_devel_like_branches(
                sessions.ansible_test_units.add_devel_like_branches
            ),
            min_version=sessions.ansible_test_units.min_version,
            max_version=sessions.ansible_test_units.max_version,
            except_versions=_convert_except_versions(
                sessions.ansible_test_units.except_versions
            ),
        )
    if sessions.ansible_test_integration_w_default_container:
        cfg = sessions.ansible_test_integration_w_default_container
        add_ansible_test_integration_sessions_default_container(
            default=cfg.default,
            include_devel=cfg.include_devel,
            include_milestone=(cfg.include_milestone),
            add_devel_like_branches=_convert_devel_like_branches(
                cfg.add_devel_like_branches
            ),
            min_version=cfg.min_version,
            max_version=cfg.max_version,
            except_versions=_convert_except_versions(cfg.except_versions),
            core_python_versions=_convert_core_python_versions(
                cfg.core_python_versions
            ),
            controller_python_versions_only=cfg.controller_python_versions_only,
            ansible_vars_from_env_vars=cfg.ansible_vars_from_env_vars,
        )
    if sessions.ansible_lint:
        add_ansible_lint(
            make_ansible_lint_default=sessions.ansible_lint.default,
            ansible_lint_package=sessions.ansible_lint.ansible_lint_package,
            strict=sessions.ansible_lint.strict,
        )
    add_matrix_generator()


def interpret_config(config: Config) -> None:
    """
    Interpret the config file's contents.
    """
    _interpret_config(config)
    _add_sessions(config.sessions)
