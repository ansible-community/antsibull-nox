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

import nox

from .ansible import AnsibleCoreVersion
from .collection import CollectionSource, setup_collection_sources
from .config import ActionGroup as ConfigActionGroup
from .config import AvoidCharacterGroup as ConfigAvoidCharacterGroup
from .config import (
    Config,
    DevelLikeBranch,
    PackageType,
    Sessions,
)
from .sessions.ansible_lint import add_ansible_lint
from .sessions.ansible_test import (
    AnsibleTestIntegrationSessionTemplate,
    AnsibleTestIntegrationSessionTemplateGroup,
    add_all_ansible_test_sanity_test_sessions,
    add_all_ansible_test_unit_test_sessions,
    add_ansible_test_integration_sessions,
    add_ansible_test_integration_sessions_default_container,
)
from .sessions.build_import_check import add_build_import_check
from .sessions.docs_check import add_docs_check
from .sessions.ee_check import (
    ExecutionEnvironmentData,
    add_execution_environment_sessions,
)
from .sessions.extra_checks import (
    ActionGroup,
    AvoidCharacterGroup,
    add_extra_checks,
)
from .sessions.license_check import add_license_check
from .sessions.lint import add_lint_sessions
from .sessions.matrix_generator import add_matrix_generator
from .sessions.utils.packages import PackageType as RuntimePackageType
from .utils import Version

_T = t.TypeVar("_T", bound=object)


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


def _convert_avoid_character_groups(
    avoid_character_groups: list[ConfigAvoidCharacterGroup] | None,
) -> list[AvoidCharacterGroup] | None:
    if avoid_character_groups is None:
        return None
    return [
        AvoidCharacterGroup(
            name=avoid_character_group.name,
            regex=avoid_character_group.regex,
            match_extensions=avoid_character_group.match_extensions,
            match_paths=avoid_character_group.match_paths,
            match_directories=avoid_character_group.match_directories,
            skip_extensions=avoid_character_group.skip_extensions,
            skip_paths=avoid_character_group.skip_paths,
            skip_directories=avoid_character_group.skip_directories,
        )
        for avoid_character_group in avoid_character_groups
    ]


def _convert_devel_like_branch(
    devel_like_branch: DevelLikeBranch | None,
) -> tuple[str | None, str] | None:
    if devel_like_branch is None:
        return None
    return devel_like_branch.repository, devel_like_branch.branch


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


def _ensure_list(value: _T | list[_T]) -> list[_T]:
    if isinstance(value, list):
        return value
    return [value]


def _ensure_list_w_none(value: _T | list[_T] | None) -> list[_T | None]:
    if isinstance(value, list):
        return value  # type: ignore
    return [value]


@t.overload
def _convert_package_name(
    package_name: PackageType | list[PackageType],
) -> list[RuntimePackageType]: ...


@t.overload
def _convert_package_name(
    package_name: list[PackageType | str],
) -> list[RuntimePackageType | str]: ...


@t.overload
def _convert_package_name(
    package_name: PackageType | list[PackageType] | None,
) -> list[RuntimePackageType] | None: ...


def _convert_package_name(
    package_name: (
        PackageType | str | list[PackageType] | list[PackageType | str] | None
    ),
) -> list[RuntimePackageType | str] | None:
    if package_name is None:
        return None
    package_name_list: list[PackageType] | list[PackageType | str] = _ensure_list(
        package_name
    )  # type: ignore
    return [
        pkg if isinstance(pkg, str) else pkg.to_utils_instance()
        for pkg in package_name_list
    ]


def _coalesce(*values: _T) -> _T | None:
    for value in values:
        if value is not None:
            return value
    return None


def _add_ansible_test_sessions(sessions: Sessions) -> None:
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

    # Handle integration tests
    integration_defaults: list[bool] = []
    if sessions.ansible_test_integration_w_default_container:
        integration_defaults.append(
            sessions.ansible_test_integration_w_default_container.default
        )
    if sessions.ansible_test_integration:
        integration_defaults.append(sessions.ansible_test_integration.default)

    default_per_int_session = len(set(integration_defaults)) == 2

    integration_sessions: list[str] = []
    if sessions.ansible_test_integration_w_default_container:
        cfg = sessions.ansible_test_integration_w_default_container
        integration_sessions.extend(
            add_ansible_test_integration_sessions_default_container(
                default=default_per_int_session and cfg.default,
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
                ansible_vars={
                    k: v.to_utils_instance() for k, v in cfg.ansible_vars.items()
                },
            )
        )
    if sessions.ansible_test_integration:
        integration_sessions.extend(
            add_ansible_test_integration_sessions(
                default=default_per_int_session
                and sessions.ansible_test_integration.default,
                ansible_vars={
                    k: v.to_utils_instance()
                    for k, v in sessions.ansible_test_integration.ansible_vars.items()
                },
                global_tags=sessions.ansible_test_integration.tags,
                session_templates=[
                    AnsibleTestIntegrationSessionTemplate(
                        ansible_core=_ensure_list(session.ansible_core),
                        docker=_ensure_list_w_none(session.docker),
                        remote=_ensure_list_w_none(session.remote),
                        python_version=_ensure_list_w_none(session.python_version),
                        target=_ensure_list_w_none(session.target),
                        gha_container=_ensure_list_w_none(session.gha_container),
                        devel_like_branch=_convert_devel_like_branch(
                            session.devel_like_branch
                        ),
                        ansible_vars={
                            k: v.to_utils_instance()
                            for k, v in session.ansible_vars.items()
                        },
                        session_name_template=session.session_name_template
                        or sessions.ansible_test_integration.session_name_template,
                        display_name_template=session.display_name_template
                        or sessions.ansible_test_integration.display_name_template,
                        description_template=session.description_template
                        or sessions.ansible_test_integration.description_template,
                        tags=session.tags,
                    )
                    for session in sessions.ansible_test_integration.sessions
                ],
                session_template_groups=[
                    AnsibleTestIntegrationSessionTemplateGroup(
                        session_name=group.session_name,
                        description=group.description,
                        ansible_vars={
                            k: v.to_utils_instance()
                            for k, v in group.ansible_vars.items()
                        },
                        tags=group.tags,
                        session_templates=[
                            AnsibleTestIntegrationSessionTemplate(
                                ansible_core=_ensure_list(session.ansible_core),
                                docker=_ensure_list_w_none(
                                    _coalesce(session.docker, group.docker)
                                ),
                                remote=_ensure_list_w_none(
                                    _coalesce(session.remote, group.remote)
                                ),
                                python_version=_ensure_list_w_none(
                                    _coalesce(
                                        session.python_version, group.python_version
                                    )
                                ),
                                target=_ensure_list_w_none(
                                    _coalesce(session.target, group.target)
                                ),
                                gha_container=_ensure_list_w_none(
                                    _coalesce(
                                        session.gha_container, group.gha_container
                                    )
                                ),
                                devel_like_branch=_convert_devel_like_branch(
                                    session.devel_like_branch
                                ),
                                ansible_vars={
                                    k: v.to_utils_instance()
                                    for k, v in session.ansible_vars.items()
                                },
                                session_name_template=session.session_name_template
                                or group.session_name_template
                                or sessions.ansible_test_integration.session_name_template,
                                display_name_template=session.display_name_template
                                or group.display_name_template
                                or sessions.ansible_test_integration.display_name_template,
                                description_template=session.description_template
                                or group.description_template
                                or sessions.ansible_test_integration.description_template,
                                tags=session.tags,
                            )
                            for session in group.sessions
                        ],
                    )
                    for group in sessions.ansible_test_integration.groups
                ],
            )
        )

    if integration_defaults:
        duplicates_check: set[str] = set()
        for name in integration_sessions:
            # nox does not warn/error on duplicate session names
            # (https://github.com/wntrblm/nox/issues/998)
            if name in duplicates_check:
                raise ValueError(
                    f"Two integration test sessions with name {name} were added!"
                )
            duplicates_check.add(name)

        def ansible_test_integration(
            session: nox.Session,  # pylint: disable=unused-argument
        ) -> None:
            pass

        ansible_test_integration.__doc__ = (
            "Meta session for running all ansible-test-integration-* sessions."
        )
        nox.session(
            name="ansible-test-integration",
            requires=integration_sessions,
            default=False if default_per_int_session else integration_defaults[0],
        )(ansible_test_integration)


def _add_sessions(sessions: Sessions) -> None:
    if sessions.lint:
        add_lint_sessions(
            make_lint_default=sessions.lint.default,
            extra_code_files=sessions.lint.extra_code_files,
            run_isort=sessions.lint.run_isort,
            isort_config=sessions.lint.isort_config,
            isort_package=_convert_package_name(sessions.lint.isort_package),
            run_black=sessions.lint.run_black,
            run_black_modules=sessions.lint.run_black_modules,
            black_config=sessions.lint.black_config,
            black_package=_convert_package_name(sessions.lint.black_package),
            run_ruff_format=sessions.lint.run_ruff_format,
            ruff_format_config=sessions.lint.ruff_format_config
            or sessions.lint.ruff_config,
            ruff_format_package=_convert_package_name(
                sessions.lint.ruff_format_package or sessions.lint.ruff_package
            ),
            run_ruff_autofix=sessions.lint.run_ruff_autofix,
            ruff_autofix_config=sessions.lint.ruff_autofix_config
            or sessions.lint.ruff_config,
            ruff_autofix_package=_convert_package_name(
                sessions.lint.ruff_autofix_package or sessions.lint.ruff_package
            ),
            ruff_autofix_select=sessions.lint.ruff_autofix_select,
            run_ruff_check=sessions.lint.run_ruff_check,
            ruff_check_config=sessions.lint.ruff_check_config
            or sessions.lint.ruff_config,
            ruff_check_package=_convert_package_name(
                sessions.lint.ruff_check_package or sessions.lint.ruff_package
            ),
            run_flake8=sessions.lint.run_flake8,
            flake8_config=sessions.lint.flake8_config,
            flake8_package=_convert_package_name(sessions.lint.flake8_package),
            run_pylint=sessions.lint.run_pylint,
            pylint_rcfile=sessions.lint.pylint_rcfile,
            pylint_modules_rcfile=sessions.lint.pylint_modules_rcfile,
            pylint_package=_convert_package_name(sessions.lint.pylint_package),
            pylint_ansible_core_package=_convert_package_name(
                sessions.lint.pylint_ansible_core_package
            ),
            pylint_extra_deps=_convert_package_name(sessions.lint.pylint_extra_deps),
            run_yamllint=sessions.lint.run_yamllint,
            yamllint_config=sessions.lint.yamllint_config,
            yamllint_config_plugins=sessions.lint.yamllint_config_plugins,
            yamllint_config_plugins_examples=sessions.lint.yamllint_config_plugins_examples,
            yamllint_config_extra_docs=sessions.lint.yamllint_config_extra_docs,
            yamllint_package=_convert_package_name(sessions.lint.yamllint_package),
            yamllint_antsibull_docutils_package=_convert_package_name(
                sessions.lint.yamllint_antsibull_docutils_package
            ),
            run_mypy=sessions.lint.run_mypy,
            mypy_config=sessions.lint.mypy_config,
            mypy_package=_convert_package_name(sessions.lint.mypy_package),
            mypy_ansible_core_package=_convert_package_name(
                sessions.lint.mypy_ansible_core_package
            ),
            mypy_extra_deps=_convert_package_name(sessions.lint.mypy_extra_deps),
            run_antsibullnox_config_lint=sessions.lint.run_antsibullnox_config_lint,
        )
    if sessions.docs_check:
        add_docs_check(
            make_docs_check_default=sessions.docs_check.default,
            antsibull_docs_package=_convert_package_name(
                sessions.docs_check.antsibull_docs_package
            ),
            ansible_core_package=_convert_package_name(
                sessions.docs_check.ansible_core_package
            ),
            validate_collection_refs=sessions.docs_check.validate_collection_refs,
            extra_collections=sessions.docs_check.extra_collections,
            codeblocks_restrict_types=sessions.docs_check.codeblocks_restrict_types,
            codeblocks_restrict_type_exact_case=(
                sessions.docs_check.codeblocks_restrict_type_exact_case
            ),
            codeblocks_allow_without_type=sessions.docs_check.codeblocks_allow_without_type,
            codeblocks_allow_literal_blocks=sessions.docs_check.codeblocks_allow_literal_blocks,
            antsibull_docutils_package=_convert_package_name(
                sessions.docs_check.antsibull_docutils_package
            ),
        )
    if sessions.license_check:
        add_license_check(
            make_license_check_default=sessions.license_check.default,
            run_reuse=sessions.license_check.run_reuse,
            reuse_package=_convert_package_name(sessions.license_check.reuse_package),
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
            run_avoid_characters=sessions.extra_checks.run_avoid_characters,
            avoid_character_group=_convert_avoid_character_groups(
                sessions.extra_checks.avoid_character_group
            ),
        )
    if sessions.build_import_check:
        add_build_import_check(
            make_build_import_check_default=sessions.build_import_check.default,
            ansible_core_package=_convert_package_name(
                sessions.build_import_check.ansible_core_package
            ),
            run_galaxy_importer=sessions.build_import_check.run_galaxy_importer,
            galaxy_importer_package=_convert_package_name(
                sessions.build_import_check.galaxy_importer_package
            ),
            galaxy_importer_config_path=sessions.build_import_check.galaxy_importer_config_path,
            galaxy_importer_always_show_logs=(
                sessions.build_import_check.galaxy_importer_always_show_logs
            ),
        )
    _add_ansible_test_sessions(sessions)
    if sessions.ansible_lint:
        add_ansible_lint(
            make_ansible_lint_default=sessions.ansible_lint.default,
            ansible_lint_package=_convert_package_name(
                sessions.ansible_lint.ansible_lint_package
            ),
            strict=sessions.ansible_lint.strict,
        )
    if sessions.ee_check:
        execution_environments = []

        for ee_config in sessions.ee_check.execution_environments:
            execution_environments.append(
                ExecutionEnvironmentData(
                    name=ee_config.name,
                    description=ee_config.description or ee_config.name,
                    config=ee_config.to_execution_environment_config(),
                    test_playbooks=ee_config.test_playbooks,
                    runtime_environment=ee_config.runtime_environment,
                    runtime_container_options=ee_config.runtime_container_options,
                    runtime_extra_vars=ee_config.runtime_extra_vars,
                )
            )

        if execution_environments:
            add_execution_environment_sessions(
                execution_environments=execution_environments,
                default=sessions.ee_check.default,
                ansible_builder_package=_convert_package_name(
                    sessions.ee_check.ansible_builder_package
                ),
                ansible_core_package=_convert_package_name(
                    sessions.ee_check.ansible_core_package
                ),
                ansible_navigator_package=_convert_package_name(
                    sessions.ee_check.ansible_navigator_package
                ),
            )
    add_matrix_generator()


def interpret_config(config: Config) -> None:
    """
    Interpret the config file's contents.
    """
    _interpret_config(config)
    _add_sessions(config.sessions)
