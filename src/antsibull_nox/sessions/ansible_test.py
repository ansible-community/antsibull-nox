# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox ansible-test sessions.
"""

from __future__ import annotations

import dataclasses
import itertools
import os
import typing as t
from collections.abc import Callable, Sequence
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
from ..cd import get_base_branch, get_vcs_name, is_config_dir_the_repo_dir
from ..container import get_container_engine_preference
from ..paths import copy_directory_tree_into
from ..python import get_installed_python_versions
from ..utils import Version
from .collections import prepare_collections
from .utils import (
    normalize_session_name,
    register,
)
from .utils.packages import (
    install,
)
from .utils.values import (
    AnsibleValue,
    AnsibleValueExplicit,
)

if t.TYPE_CHECKING:
    DevelLikeBranch = tuple[str | None, str]


def get_ansible_test_env() -> dict[str, str]:
    """
    Set ANSIBLE_TEST_PREFER_PODMAN if the user prefers one of podman or docker over the other.
    """
    # Check whether the user explicitly set ANSIBLE_TEST_PREFER_PODMAN
    if os.environ.get("ANSIBLE_TEST_PREFER_PODMAN") is not None:
        return {}
    # Check whether the user explicitly requested a container engine for antsibull-nox
    preference, explicitly_set = get_container_engine_preference()
    if not explicitly_set:
        return {}
    # Check whether the users prefers one of podman and docker over the other
    if preference in ("auto-prefer-podman", "podman"):
        # Yes, the user prefers podman.
        return {"ANSIBLE_TEST_PREFER_PODMAN": "1"}
    if preference in ("auto-prefer-docker", "docker"):
        # Yes, the user prefers docker.
        return {"ANSIBLE_TEST_PREFER_PODMAN": ""}
    # Apparently not: do nothing.
    return {}


# NOTE: This is publicly documented API!
# Any change to the API must not be breaking, and must be
# updated in docs/reference.md!
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
    register_tags: Sequence[str] | None = None,
    callback_before: Callable[[], None] | None = None,
    callback_after: Callable[[], None] | None = None,
    support_cd: bool = False,
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

        change_detection_args: list[str] | None = None
        if support_cd and get_vcs_name() == "git" and is_config_dir_the_repo_dir():
            base_branch = get_base_branch()
            if base_branch is not None:
                change_detection_args = [
                    "--changed",
                    "--untracked",
                    "--base-branch",
                    base_branch,
                ]

        prepared_collections = prepare_collections(
            session,
            ansible_core_version=parsed_ansible_core_version,
            install_in_site_packages=False,
            extra_deps_files=extra_deps_files,
            install_out_of_tree=True,
            copy_repo_structure=change_detection_args is not None,
        )
        if not prepared_collections:
            session.warn("Skipping ansible-test...")
            return
        cwd = Path.cwd()
        with session.chdir(prepared_collections.current_path):
            if callback_before:
                callback_before()

            command = ["ansible-test"] + ansible_test_params
            if change_detection_args is not None:
                command.extend(change_detection_args)
            if add_posargs and session.posargs:
                command.extend(session.posargs)
            session.run(*command, env=get_ansible_test_env())

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
        data: dict[str, t.Any] = {
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
        if register_tags:
            data["tags"] = sorted(register_tags)
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
        register_tags=["sanity", "docker"],
        support_cd=True,
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
    add_devel_like_branches: list[DevelLikeBranch] | None = None,
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
        register_tags=["units", "docker"],
        support_cd=True,
    )


def add_all_ansible_test_unit_test_sessions(
    *,
    default: bool = False,
    include_devel: bool = False,
    include_milestone: bool = False,
    add_devel_like_branches: list[DevelLikeBranch] | None = None,
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


def update_gitignore(gitignore_path: Path, *paths_to_add: Path) -> None:
    """
    Add the given paths to .gitignore.
    """
    if not paths_to_add:
        return

    existing: list[str]
    try:
        with open(gitignore_path, encoding="utf-8", mode="rt") as f:
            existing = [f.read()]
    except FileNotFoundError:
        existing = [""]

    for path in paths_to_add:
        existing.append(f"/{path}")
    existing.append("")

    with open(gitignore_path, encoding="utf-8", mode="wt") as f:
        f.write("\n".join(existing))


def write_integration_config(
    *ansible_vars: dict[str, AnsibleValue] | None,
    ansible_vars_from_env_vars: dict[str, str] | None = None,
) -> None:
    """
    Write tests/integration/integration_config.yml with the provided values.
    """
    path = Path("tests", "integration", "integration_config.yml")
    content: dict[str, t.Any] = {}

    if ansible_vars_from_env_vars:
        for ans_var, env_var in ansible_vars_from_env_vars.items():
            value = os.environ.get(env_var)
            if value is not None:
                content[ans_var] = env_var

    for one_ansible_vars in ansible_vars:
        if one_ansible_vars:
            for ans_var, ans_value in one_ansible_vars.items():
                val, store = ans_value.get_value()
                if store:
                    content[ans_var] = val

    store_yaml_file(path, content, nice=True, sort_keys=True)

    update_gitignore(
        Path(".gitignore"),
        path,
    )


def add_ansible_test_integration_sessions_default_container(
    *,
    include_devel: bool = False,
    include_milestone: bool = False,
    add_devel_like_branches: list[DevelLikeBranch] | None = None,
    min_version: Version | str | None = None,
    max_version: Version | str | None = None,
    except_versions: list[AnsibleCoreVersion | str] | None = None,
    core_python_versions: (
        dict[str | AnsibleCoreVersion, list[str | Version]] | None
    ) = None,
    controller_python_versions_only: bool = False,
    ansible_vars_from_env_vars: dict[str, str] | None = None,
    ansible_vars: dict[str, AnsibleValue] | None = None,
    default: bool = False,
) -> list[str]:
    """
    Add ansible-test integration tests using the default Docker container.

    ``core_python_versions`` can be used to restrict the Python versions
    to be used for a specific ansible-core version.

    ``controller_python_versions_only`` can be used to only run against
    controller Python versions.
    """

    def callback_before() -> None:
        if not ansible_vars_from_env_vars and not ansible_vars:
            return

        write_integration_config(
            ansible_vars, ansible_vars_from_env_vars=ansible_vars_from_env_vars
        )

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
                register_tags=["integration", "docker", "docker-default"],
                support_cd=True,
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
                default=default,
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
                    default=default,
                )(run_integration_tests_for_branch)

    return integration_sessions


@dataclasses.dataclass
class AnsibleTestIntegrationSessionTemplate:
    """
    A template for an ansible-test integration test session.
    """

    ansible_core: list[AnsibleCoreVersion]
    docker: list[str | None]
    remote: list[str | None]
    python_version: list[Version | None]
    target: list[str | None]
    gha_container: list[str | None]

    devel_like_branch: DevelLikeBranch | None

    ansible_vars: dict[str, AnsibleValue]
    session_name_template: str
    display_name_template: str
    description_template: str
    tags: list[str]


@dataclasses.dataclass
class AnsibleTestIntegrationSessionTemplateGroup:
    """
    A template for an ansible-test integration test session.
    """

    session_name: str | None
    description: str | None
    ansible_vars: dict[str, AnsibleValue]
    session_templates: list[AnsibleTestIntegrationSessionTemplate]
    tags: list[str]


@dataclasses.dataclass
class AnsibleTestIntegrationSession:
    """
    A template for an ansible-test integration test session.
    """

    source: str
    part_of_group: bool

    ansible_core: AnsibleCoreVersion
    ansible_core_repo_name: str | None
    ansible_core_branch_name: str | None
    docker: str | None
    remote: str | None
    python_version: Version | None
    target: str | None
    gha_container: str | None

    ansible_vars: dict[str, AnsibleValue]
    session_name: str
    display_name: str
    description: str
    tags: list[str]

    def get_ansible_vars_callback(self) -> t.Callable[[], None] | None:
        """
        Create before-callback for ansible-test.
        """
        if not self.ansible_vars:
            return None

        def callback_before() -> None:
            write_integration_config(self.ansible_vars)

        return callback_before


@dataclasses.dataclass
class AnsibleTestIntegrationSessionGroup:
    """
    A template for an ansible-test integration test session.
    """

    session_name: str | None
    description: str | None
    sessions: list[AnsibleTestIntegrationSession]


def _get_templator(**kwargs: t.Any) -> t.Callable[[str], str]:
    template_vars = {}
    for k, v in kwargs.items():
        val = str(v) if v is not None else ""
        template_vars[k] = val
        template_vars[f"{k}_dash"] = f"{val}-" if val else ""
        template_vars[f"dash_{k}"] = f"-{val}" if val else ""
        template_vars[f"{k}_plus"] = f"{val}+" if val else ""
        template_vars[f"plus_{k}"] = f"+{val}" if val else ""
        template_vars[f"{k}_comma"] = f"{val}, " if val else ""
        template_vars[f"comma_{k}"] = f", {val}" if val else ""

    def tmpl(template: str) -> str:
        try:
            return template.format(**template_vars)
        except KeyError as exc:
            raise ValueError(
                f"Error when templating {template!r}: unknown variable {str(exc)!r}"
            ) from None

    return tmpl


def _template_session(
    session_template: AnsibleTestIntegrationSessionTemplate,
    source: str,
    part_of_group: bool,
    ansible_vars: list[dict[str, AnsibleValue] | None],
    tags: set[str] | list[str],
) -> t.Generator[AnsibleTestIntegrationSession]:
    session_ansible_vars = {}
    for ansible_vars_item in ansible_vars:
        if ansible_vars_item:
            session_ansible_vars.update(ansible_vars_item)
    session_ansible_vars.update(session_template.ansible_vars)
    vars_values: dict[str, t.Any] = {}
    for var, value in session_ansible_vars.items():
        if value.template_value is not None:
            vars_values[var] = value.template_value
        elif isinstance(value, AnsibleValueExplicit):
            vars_values[var] = value.value
    session_tags = set(tags)
    session_tags.update(session_template.tags)
    tags_list = sorted(session_tags)
    for (
        ansible_core,
        docker,
        remote,
        python_version,
        target,
        gha_container,
    ) in itertools.product(
        session_template.ansible_core,
        session_template.docker,
        session_template.remote,
        session_template.python_version,
        session_template.target,
        session_template.gha_container,
    ):
        gha_arm = gha_container and "-arm" in gha_container
        vars_values.update(
            {
                "ansible_core": ansible_core,
                "docker": docker,
                "docker_short": (
                    (
                        docker.removeprefix(
                            "quay.io/ansible-community/test-image:"
                        ).removeprefix("localhost/test-image:")
                    )
                    if docker
                    else None
                ),
                "remote": remote,
                "python_version": python_version,
                "py_python_version": f"py{python_version}" if python_version else None,
                "target": target,
                "target_dashized": (
                    target.replace("/", "-").strip("-") if target else None
                ),
                "gha_container": gha_container,
                "gha_arm": "ARM" if gha_arm else None,
                "gha_arm_lower": "arm" if gha_arm else None,
            }
        )
        tmpl = _get_templator(**vars_values)
        yield AnsibleTestIntegrationSession(
            source=source,
            part_of_group=part_of_group,
            ansible_core=ansible_core,
            ansible_core_repo_name=(
                session_template.devel_like_branch[0]
                if ansible_core == "devel" and session_template.devel_like_branch
                else None
            ),
            ansible_core_branch_name=(
                session_template.devel_like_branch[1]
                if ansible_core == "devel" and session_template.devel_like_branch
                else None
            ),
            docker=docker,
            remote=remote,
            python_version=python_version,
            target=target,
            gha_container=gha_container,
            ansible_vars=session_ansible_vars,
            session_name=normalize_session_name(
                tmpl(session_template.session_name_template)
            ),
            display_name=tmpl(session_template.display_name_template),
            description=tmpl(session_template.description_template),
            tags=tags_list,
        )


def _template_sessions(
    session_templates: list[AnsibleTestIntegrationSessionTemplate],
    session_template_groups: list[AnsibleTestIntegrationSessionTemplateGroup],
    ansible_vars: dict[str, AnsibleValue],
    tags: list[str],
) -> tuple[
    list[AnsibleTestIntegrationSession], list[AnsibleTestIntegrationSessionGroup]
]:
    result: list[AnsibleTestIntegrationSession] = []
    result_groups: list[AnsibleTestIntegrationSessionGroup] = []
    for index, template in enumerate(session_templates):
        for session in _template_session(
            template, f"session template #{index + 1}", False, [ansible_vars], tags
        ):
            result.append(session)
    for group_index, group in enumerate(session_template_groups):
        group_sessions: list[AnsibleTestIntegrationSession] = []
        group_tags = set(tags)
        group_tags.update(group.tags)
        for index, template in enumerate(group.session_templates):
            for session in _template_session(
                template,
                f"session template #{index + 1} of group #{group_index + 1}",
                True,
                [ansible_vars, group.ansible_vars],
                group_tags,
            ):
                result.append(session)
                group_sessions.append(session)
        result_groups.append(
            AnsibleTestIntegrationSessionGroup(
                session_name=group.session_name,
                description=group.description,
                sessions=group_sessions,
            )
        )
    return result, result_groups


def add_ansible_test_integration_sessions(
    *,
    session_templates: list[AnsibleTestIntegrationSessionTemplate] | None = None,
    session_template_groups: (
        list[AnsibleTestIntegrationSessionTemplateGroup] | None
    ) = None,
    ansible_vars: dict[str, AnsibleValue] | None = None,
    global_tags: list[str] | None = None,
    default: bool = False,
) -> list[str]:
    """
    Add ansible-test integration tests.
    """
    sessions, groups = _template_sessions(
        session_templates or [],
        session_template_groups or [],
        ansible_vars or {},
        global_tags or [],
    )
    session_by_name: dict[str, AnsibleTestIntegrationSession] = {}
    for session in sessions:
        # nox does not warn/error on duplicate session names
        # (https://github.com/wntrblm/nox/issues/998)
        if session.session_name in session_by_name:
            raise ValueError(
                f"Collision: {session.source} and {session_by_name[session.session_name].source}"
                f" both generated the same session name {session.session_name!r}"
            )
        session_by_name[session.session_name] = session

    for _, session in sorted(session_by_name.items()):
        register_tags = ["integration"] + session.tags
        cmd = [
            "integration",
            "--color",
            "-v",
        ]
        if session.docker:
            cmd.extend(
                [
                    "--docker",
                    session.docker,
                ]
            )
            register_tags.extend(["docker", f"docker-{session.docker}"])
        if session.remote:
            cmd.extend(
                [
                    "--remote",
                    session.remote,
                ]
            )
            register_tags.extend(["remote", f"remote-{session.remote}"])
        if session.python_version:
            cmd.extend(
                [
                    "--python",
                    str(session.python_version),
                ]
            )
            register_tags.extend(["python", f"python-{session.python_version}"])
        if session.target:
            cmd.append(session.target)
        extra_data = {
            "display-name": session.display_name,
        }
        if session.gha_container is not None:
            extra_data["gha-container"] = session.gha_container
        add_ansible_test_session(
            name=session.session_name,
            description=session.description,
            ansible_test_params=cmd,
            extra_deps_files=["tests/integration/requirements.yml"],
            ansible_core_version=session.ansible_core,
            ansible_core_repo_name=session.ansible_core_repo_name,
            ansible_core_branch_name=session.ansible_core_repo_name,
            callback_before=session.get_ansible_vars_callback(),
            default=default and not session.part_of_group,
            register_name="integration",
            register_extra_data=extra_data,
            register_tags=sorted(register_tags),
            support_cd=True,
        )

    def add_group_session(
        session_name: str, description: str, session_names: list[str]
    ) -> None:
        def ansible_test_group(
            session: nox.Session,  # pylint: disable=unused-argument
        ) -> None:
            pass

        ansible_test_group.__doc__ = description
        nox.session(
            name=session_name,
            requires=sorted(session_names),
            default=default,
        )(ansible_test_group)

    for group in groups:
        if group.session_name is None:
            continue
        add_group_session(
            normalize_session_name(group.session_name),
            group.description
            or "Meta session for running some ansible-test integration test sessions.",
            [session.session_name for session in group.sessions],
        )

    return sorted(session_by_name)


__all__ = [
    "AnsibleTestIntegrationSessionTemplate",
    "AnsibleTestIntegrationSessionTemplateGroup",
    "add_ansible_test_session",
    "add_ansible_test_sanity_test_session",
    "add_all_ansible_test_sanity_test_sessions",
    "add_ansible_test_unit_test_session",
    "add_all_ansible_test_unit_test_sessions",
    "add_ansible_test_integration_sessions_default_container",
    "add_ansible_test_integration_sessions",
]
