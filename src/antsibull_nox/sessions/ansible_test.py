# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox ansible-test sessions.
"""

from __future__ import annotations

import os
import typing as t
from collections.abc import Callable
from pathlib import Path

import nox
from antsibull_fileutils.yaml import store_yaml_file

from ..ansible import (
    AnsibleCoreVersion,
    get_ansible_core_info,
    get_ansible_core_package_name,
    get_supported_core_versions,
    parse_ansible_core_version,
)
from ..paths import copy_directory_tree_into
from ..python import get_installed_python_versions
from ..utils import Version
from .collections import prepare_collections
from .utils import (
    install,
    register,
)


def add_ansible_test_session(
    *,
    name: str,
    description: str | None,
    extra_deps_files: list[str | os.PathLike] | None = None,
    ansible_test_params: list[str],
    add_posargs: bool = True,
    default: bool,
    ansible_core_version: str | AnsibleCoreVersion,
    ansible_core_source: t.Literal["git", "pypi"] = "git",
    ansible_core_repo_name: str | None = None,
    ansible_core_branch_name: str | None = None,
    handle_coverage: t.Literal["never", "always", "auto"] = "auto",
    register_name: str | None = None,
    register_extra_data: dict[str, t.Any] | None = None,
    callback_before: Callable[[], None] | None = None,
    callback_after: Callable[[], None] | None = None,
) -> None:
    """
    Add generic ansible-test session.

    Returns a list of Python versions set for this session.
    """
    parsed_ansible_core_version = parse_ansible_core_version(ansible_core_version)

    def compose_dependencies() -> list[str]:
        deps = [
            get_ansible_core_package_name(
                parsed_ansible_core_version,
                source=ansible_core_source,
                ansible_repo=ansible_core_repo_name,
                branch_name=ansible_core_branch_name,
            )
        ]
        return deps

    def run_ansible_test(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        prepared_collections = prepare_collections(
            session,
            ansible_core_version=parsed_ansible_core_version,
            install_in_site_packages=False,
            extra_deps_files=extra_deps_files,
            install_out_of_tree=True,
        )
        if not prepared_collections:
            session.warn("Skipping ansible-test...")
            return
        cwd = Path.cwd()
        with session.chdir(prepared_collections.current_path):
            if callback_before:
                callback_before()

            command = ["ansible-test"] + ansible_test_params
            if add_posargs and session.posargs:
                command.extend(session.posargs)
            session.run(*command)

            coverage = (handle_coverage == "auto" and "--coverage" in command) or (
                handle_coverage == "always"
            )
            if coverage:
                session.run(
                    "ansible-test",
                    "coverage",
                    "xml",
                    "--color",
                    "-v",
                    "--requirements",
                    "--group-by",
                    "command",
                    "--group-by",
                    "version",
                )

            if callback_after:
                callback_after()

            copy_directory_tree_into(
                prepared_collections.current_path / "tests" / "output",
                cwd / "tests" / "output",
            )

    # Determine Python version(s)
    core_info = get_ansible_core_info(parsed_ansible_core_version)
    all_versions = get_installed_python_versions()

    installed_versions = [
        version
        for version in core_info.controller_python_versions
        if version in all_versions
    ]
    python = max(installed_versions or core_info.controller_python_versions)
    python_versions = [python]

    run_ansible_test.__doc__ = description
    nox.session(
        name=name,
        default=default,
        python=[str(python_version) for python_version in python_versions],
    )(run_ansible_test)

    if register_name:
        data = {
            "name": name,
            "ansible-core": (
                str(ansible_core_branch_name)
                if ansible_core_branch_name is not None
                else str(parsed_ansible_core_version)
            ),
            "python": " ".join(str(python) for python in python_versions),
        }
        if register_extra_data:
            data.update(register_extra_data)
        register(register_name, data)


def add_ansible_test_sanity_test_session(
    *,
    name: str,
    description: str | None,
    default: bool,
    ansible_core_version: str | AnsibleCoreVersion,
    ansible_core_source: t.Literal["git", "pypi"] = "git",
    ansible_core_repo_name: str | None = None,
    ansible_core_branch_name: str | None = None,
    skip_tests: list[str] | None = None,
    allow_disabled: bool = False,
    enable_optional_errors: bool = False,
    register_extra_data: dict[str, t.Any] | None = None,
) -> None:
    """
    Add generic ansible-test sanity test session.
    """
    command = ["sanity", "--color", "-v", "--docker"]
    if skip_tests:
        for test in skip_tests:
            command.extend(["--skip", test])
    if allow_disabled:
        command.append("--allow-disabled")
    if enable_optional_errors:
        command.append("--enable-optional-errors")
    add_ansible_test_session(
        name=name,
        description=description,
        ansible_test_params=command,
        default=default,
        ansible_core_version=ansible_core_version,
        ansible_core_source=ansible_core_source,
        ansible_core_repo_name=ansible_core_repo_name,
        ansible_core_branch_name=ansible_core_branch_name,
        register_name="sanity",
        register_extra_data=register_extra_data,
    )


def _parse_min_max_except(
    min_version: Version | str | None,
    max_version: Version | str | None,
    except_versions: list[AnsibleCoreVersion | str] | None,
) -> tuple[Version | None, Version | None, tuple[AnsibleCoreVersion, ...] | None]:
    if isinstance(min_version, str):
        min_version = Version.parse(min_version)
    if isinstance(max_version, str):
        max_version = Version.parse(max_version)
    if except_versions is None:
        return min_version, max_version, None
    evs = tuple(parse_ansible_core_version(version) for version in except_versions)
    return min_version, max_version, evs


def add_all_ansible_test_sanity_test_sessions(
    *,
    default: bool = False,
    include_devel: bool = False,
    include_milestone: bool = False,
    add_devel_like_branches: list[tuple[str | None, str]] | None = None,
    min_version: Version | str | None = None,
    max_version: Version | str | None = None,
    except_versions: list[AnsibleCoreVersion | str] | None = None,
    skip_tests: list[str] | None = None,
    allow_disabled: bool = False,
    enable_optional_errors: bool = False,
) -> None:
    """
    Add ansible-test sanity test meta session that runs ansible-test sanity
    for all supported ansible-core versions.
    """
    parsed_min_version, parsed_max_version, parsed_except_versions = (
        _parse_min_max_except(min_version, max_version, except_versions)
    )

    sanity_sessions = []
    for ansible_core_version in get_supported_core_versions(
        include_devel=include_devel,
        include_milestone=include_milestone,
        min_version=parsed_min_version,
        max_version=parsed_max_version,
        except_versions=parsed_except_versions,
    ):
        name = f"ansible-test-sanity-{ansible_core_version}"
        add_ansible_test_sanity_test_session(
            name=name,
            description=f"Run sanity tests from ansible-core {ansible_core_version}'s ansible-test",
            ansible_core_version=ansible_core_version,
            skip_tests=skip_tests,
            allow_disabled=allow_disabled,
            enable_optional_errors=enable_optional_errors,
            register_extra_data={"display-name": f"Ⓐ{ansible_core_version}"},
            default=False,
        )
        sanity_sessions.append(name)
    if add_devel_like_branches:
        for repo_name, branch_name in add_devel_like_branches:
            repo_prefix = (
                f"{repo_name.replace('/', '-')}-" if repo_name is not None else ""
            )
            repo_postfix = f", {repo_name} repository" if repo_name is not None else ""
            name = f"ansible-test-sanity-{repo_prefix}{branch_name.replace('/', '-')}"
            add_ansible_test_sanity_test_session(
                name=name,
                description=(
                    "Run sanity tests from ansible-test in ansible-core's"
                    f" {branch_name} branch{repo_postfix}"
                ),
                ansible_core_version="devel",
                ansible_core_repo_name=repo_name,
                ansible_core_branch_name=branch_name,
                skip_tests=skip_tests,
                allow_disabled=allow_disabled,
                enable_optional_errors=enable_optional_errors,
                register_extra_data={"display-name": f"Ⓐ{branch_name}"},
                default=False,
            )
            sanity_sessions.append(name)

    def run_all_sanity_tests(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        pass

    run_all_sanity_tests.__doc__ = (
        "Meta session for running all ansible-test-sanity-* sessions."
    )
    nox.session(
        name="ansible-test-sanity",
        default=default,
        requires=sanity_sessions,
    )(run_all_sanity_tests)


def add_ansible_test_unit_test_session(
    *,
    name: str,
    description: str | None,
    default: bool,
    ansible_core_version: str | AnsibleCoreVersion,
    ansible_core_source: t.Literal["git", "pypi"] = "git",
    ansible_core_repo_name: str | None = None,
    ansible_core_branch_name: str | None = None,
    register_extra_data: dict[str, t.Any] | None = None,
) -> None:
    """
    Add generic ansible-test unit test session.
    """
    add_ansible_test_session(
        name=name,
        description=description,
        ansible_test_params=["units", "--color", "-v", "--docker"],
        extra_deps_files=["tests/unit/requirements.yml"],
        default=default,
        ansible_core_version=ansible_core_version,
        ansible_core_source=ansible_core_source,
        ansible_core_repo_name=ansible_core_repo_name,
        ansible_core_branch_name=ansible_core_branch_name,
        register_name="units",
        register_extra_data=register_extra_data,
    )


def add_all_ansible_test_unit_test_sessions(
    *,
    default: bool = False,
    include_devel: bool = False,
    include_milestone: bool = False,
    add_devel_like_branches: list[tuple[str | None, str]] | None = None,
    min_version: Version | str | None = None,
    max_version: Version | str | None = None,
    except_versions: list[AnsibleCoreVersion | str] | None = None,
) -> None:
    """
    Add ansible-test unit test meta session that runs ansible-test units
    for all supported ansible-core versions.
    """
    parsed_min_version, parsed_max_version, parsed_except_versions = (
        _parse_min_max_except(min_version, max_version, except_versions)
    )

    units_sessions = []
    for ansible_core_version in get_supported_core_versions(
        include_devel=include_devel,
        include_milestone=include_milestone,
        min_version=parsed_min_version,
        max_version=parsed_max_version,
        except_versions=parsed_except_versions,
    ):
        name = f"ansible-test-units-{ansible_core_version}"
        add_ansible_test_unit_test_session(
            name=name,
            description=f"Run unit tests with ansible-core {ansible_core_version}'s ansible-test",
            ansible_core_version=ansible_core_version,
            register_extra_data={"display-name": f"Ⓐ{ansible_core_version}"},
            default=False,
        )
        units_sessions.append(name)
    if add_devel_like_branches:
        for repo_name, branch_name in add_devel_like_branches:
            repo_prefix = (
                f"{repo_name.replace('/', '-')}-" if repo_name is not None else ""
            )
            repo_postfix = f", {repo_name} repository" if repo_name is not None else ""
            name = f"ansible-test-units-{repo_prefix}{branch_name.replace('/', '-')}"
            add_ansible_test_unit_test_session(
                name=name,
                description=(
                    "Run unit tests from ansible-test in ansible-core's"
                    f" {branch_name} branch{repo_postfix}"
                ),
                ansible_core_version="devel",
                ansible_core_repo_name=repo_name,
                ansible_core_branch_name=branch_name,
                register_extra_data={"display-name": f"Ⓐ{branch_name}"},
                default=False,
            )
            units_sessions.append(name)

    def run_all_unit_tests(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        pass

    run_all_unit_tests.__doc__ = (
        "Meta session for running all ansible-test-units-* sessions."
    )
    nox.session(
        name="ansible-test-units",
        default=default,
        requires=units_sessions,
    )(run_all_unit_tests)


def add_ansible_test_integration_sessions_default_container(
    *,
    include_devel: bool = False,
    include_milestone: bool = False,
    add_devel_like_branches: list[tuple[str | None, str]] | None = None,
    min_version: Version | str | None = None,
    max_version: Version | str | None = None,
    except_versions: list[AnsibleCoreVersion | str] | None = None,
    core_python_versions: (
        dict[str | AnsibleCoreVersion, list[str | Version]] | None
    ) = None,
    controller_python_versions_only: bool = False,
    ansible_vars_from_env_vars: dict[str, str] | None = None,
    default: bool = False,
) -> None:
    """
    Add ansible-test integration tests using the default Docker container.

    ``core_python_versions`` can be used to restrict the Python versions
    to be used for a specific ansible-core version.

    ``controller_python_versions_only`` can be used to only run against
    controller Python versions.
    """

    def callback_before() -> None:
        if not ansible_vars_from_env_vars:
            return

        path = Path("tests", "integration", "integration_config.yml")
        content: dict[str, t.Any] = {}
        for ans_var, env_var in ansible_vars_from_env_vars.items():
            value = os.environ.get(env_var)
            if value is not None:
                content[ans_var] = env_var
        store_yaml_file(path, content, nice=True, sort_keys=True)

    def add_integration_tests(
        ansible_core_version: AnsibleCoreVersion,
        repo_name: str | None = None,
        branch_name: str | None = None,
    ) -> list[str]:
        # Determine Python versions to run tests for
        py_versions = (
            (core_python_versions.get(branch_name) if branch_name is not None else None)
            or core_python_versions.get(ansible_core_version)
            or core_python_versions.get(str(ansible_core_version))
            if core_python_versions
            else None
        )
        if py_versions is None:
            core_info = get_ansible_core_info(ansible_core_version)
            py_versions = list(
                core_info.controller_python_versions
                if controller_python_versions_only
                else core_info.remote_python_versions
            )

        # Add sessions
        integration_sessions_core: list[str] = []
        if branch_name is None:
            base_name = f"ansible-test-integration-{ansible_core_version}-"
        else:
            repo_prefix = (
                f"{repo_name.replace('/', '-')}-" if repo_name is not None else ""
            )
            base_name = f"ansible-test-integration-{repo_prefix}{branch_name.replace('/', '-')}-"
        for py_version in py_versions:
            name = f"{base_name}{py_version}"
            if branch_name is None:
                description = (
                    f"Run integration tests from ansible-core {ansible_core_version}'s"
                    f" ansible-test with Python {py_version}"
                )
            else:
                repo_postfix = (
                    f", {repo_name} repository" if repo_name is not None else ""
                )
                description = (
                    f"Run integration tests from ansible-test in ansible-core's {branch_name}"
                    f" branch{repo_postfix} with Python {py_version}"
                )
            add_ansible_test_session(
                name=name,
                description=description,
                ansible_test_params=[
                    "integration",
                    "--color",
                    "-v",
                    "--docker",
                    "default",
                    "--python",
                    str(py_version),
                ],
                extra_deps_files=["tests/integration/requirements.yml"],
                ansible_core_version=ansible_core_version,
                ansible_core_repo_name=repo_name,
                ansible_core_branch_name=branch_name,
                callback_before=callback_before,
                default=False,
                register_name="integration",
                register_extra_data={
                    "display-name": f"Ⓐ{ansible_core_version}+py{py_version}+default"
                },
            )
            integration_sessions_core.append(name)
        return integration_sessions_core

    parsed_min_version, parsed_max_version, parsed_except_versions = (
        _parse_min_max_except(min_version, max_version, except_versions)
    )
    integration_sessions: list[str] = []
    for ansible_core_version in get_supported_core_versions(
        include_devel=include_devel,
        include_milestone=include_milestone,
        min_version=parsed_min_version,
        max_version=parsed_max_version,
        except_versions=parsed_except_versions,
    ):
        integration_sessions_core = add_integration_tests(ansible_core_version)
        if integration_sessions_core:
            name = f"ansible-test-integration-{ansible_core_version}"
            integration_sessions.append(name)

            def run_integration_tests(
                session: nox.Session,  # pylint: disable=unused-argument
            ) -> None:
                pass

            run_integration_tests.__doc__ = (
                f"Meta session for running all {name}-* sessions."
            )
            nox.session(
                name=name,
                requires=integration_sessions_core,
                default=False,
            )(run_integration_tests)
    if add_devel_like_branches:
        for repo_name, branch_name in add_devel_like_branches:
            integration_sessions_core = add_integration_tests(
                "devel", repo_name=repo_name, branch_name=branch_name
            )
            if integration_sessions_core:
                repo_prefix = (
                    f"{repo_name.replace('/', '-')}-" if repo_name is not None else ""
                )
                name = f"ansible-test-integration-{repo_prefix}{branch_name.replace('/', '-')}"
                integration_sessions.append(name)

                def run_integration_tests_for_branch(
                    session: nox.Session,  # pylint: disable=unused-argument
                ) -> None:
                    pass

                run_integration_tests_for_branch.__doc__ = (
                    f"Meta session for running all {name}-* sessions."
                )
                nox.session(
                    name=name,
                    requires=integration_sessions_core,
                    default=False,
                )(run_integration_tests_for_branch)

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
        default=default,
    )(ansible_test_integration)


__all__ = [
    "add_ansible_test_session",
    "add_ansible_test_sanity_test_session",
    "add_all_ansible_test_sanity_test_sessions",
    "add_ansible_test_unit_test_session",
    "add_all_ansible_test_unit_test_sessions",
    "add_ansible_test_integration_sessions_default_container",
]
