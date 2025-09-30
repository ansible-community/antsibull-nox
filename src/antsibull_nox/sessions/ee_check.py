# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Build execution environments for testing.
"""

from __future__ import annotations

import shutil
import typing as t
from dataclasses import dataclass
from pathlib import Path

import nox

from antsibull_nox.ee_config import generate_ee_config
from antsibull_nox.paths import get_outside_temp_directory

from ..collection import CollectionData, build_collection
from ..container import get_container_engine_preference, get_preferred_container_engine
from .utils import register
from .utils.packages import (
    PackageType,
    PackageTypeOrList,
    check_package_types,
    install,
    normalize_package_type,
)


@dataclass
class ExecutionEnvironmentData:
    """
    Information for an execution environment session.
    """

    name: str
    description: str
    config: dict[str, t.Any]
    test_playbooks: list[str]
    runtime_environment: dict[str, str] | None = None
    runtime_container_options: list[str] | None = None
    runtime_extra_vars: dict[str, str] | None = None


def build_ee_image(
    *,
    session: nox.Session,
    directory: Path,
    ee_name: str,
    collection_data: CollectionData,
    container_engine: str,
) -> str:
    """
    Build container images for execution environments.

    Args:
        session: Nox session object
        directory: Path to directory that contains execution environment definition
        ee_name: Name of execution environment
        collection_data: Collection information
        container_engine: Container runtime to use

    Returns:
        Name of successfully built container image
    """
    image_name = f"{collection_data.namespace}-{collection_data.name}-{ee_name}"
    cmd = [
        "ansible-builder",
        "build",
        "--file",
        "execution-environment.yml",
        "--tag",
        image_name,
        "--container-runtime",
        container_engine,
        "--verbosity",
        "3",
        "--context",
        str(directory),
    ]
    with session.chdir(directory):
        session.run(*cmd)  # , silent=True)
    return image_name


def prepare_execution_environment(
    *,
    session: nox.Session,
    execution_environment: ExecutionEnvironmentData,
    container_engine: str,
) -> tuple[Path | None, str | None, CollectionData]:
    """
    Generate execution environments for a collection.

    Args:
        session: Nox session object
        execution_environment: EE configuration data
        container_engine: Container runtime to use

    Returns:
        Tuple with:
        - collection_tarball_path: Path to the built collection tarball
        - built_image_names: List of built container images
        - collection_data: Collection metadata
    """
    collection_tarball_path, collection_data, _ = build_collection(session)

    if collection_tarball_path is None:
        return collection_tarball_path, None, collection_data

    directory = Path(session.create_tmp()) / "ee"
    if directory.is_dir():
        shutil.rmtree(directory)
    if not directory.is_dir():
        directory.mkdir()

    generate_ee_config(
        directory=directory,
        collection_tarball_path=collection_tarball_path.absolute(),
        collection_data=collection_data,
        ee_config=execution_environment.config,
    )

    built_image = build_ee_image(
        session=session,
        directory=directory,
        ee_name=execution_environment.name,
        collection_data=collection_data,
        container_engine=container_engine,
    )

    return collection_tarball_path, built_image, collection_data


def add_execution_environment_session(
    *,
    session_name: str,
    execution_environment: ExecutionEnvironmentData,
    default: bool = False,
    ansible_builder_package: PackageTypeOrList = "ansible-builder",
    ansible_core_package: PackageTypeOrList | None = None,
    ansible_navigator_package: PackageTypeOrList = "ansible-navigator",
) -> None:
    """
    Build and test execution environments for the collection.
    """

    def compose_dependencies(session: nox.Session) -> list[PackageType]:
        result = []
        result.extend(
            check_package_types(
                session,
                "sessions.ee_check.ansible_builder_package",
                normalize_package_type(ansible_builder_package),
            )
        )
        result.extend(
            check_package_types(
                session,
                "sessions.ee_check.ansible_navigator_package",
                normalize_package_type(ansible_navigator_package),
            )
        )
        result.extend(
            check_package_types(
                session,
                "sessions.ee_check.ansible_core_package",
                normalize_package_type(ansible_core_package),
            )
        )
        return result

    def session_func(session: nox.Session) -> None:
        install(session, *compose_dependencies(session))

        container_engine = get_preferred_container_engine()
        session.log(f"Using container engine {container_engine}")

        collection_tarball, built_image, collection_data = (
            prepare_execution_environment(
                session=session,
                execution_environment=execution_environment,
                container_engine=container_engine,
            )
        )

        if collection_tarball is None or built_image is None:
            # Install only
            return

        session.log(
            f"Building execution environment {execution_environment.description}"
            f" for {collection_data.namespace}.{collection_data.name}. Image: {built_image}"
            f" using {container_engine}"
        )

        playbook_dir = Path.cwd()
        temp_dir = get_outside_temp_directory(playbook_dir.absolute())

        for playbook in execution_environment.test_playbooks:
            env = {"TMPDIR": str(temp_dir)}
            command = [
                "ansible-navigator",
                "run",
                "--mode",
                "stdout",
                "--container-engine",
                container_engine,
            ]
            if execution_environment.runtime_container_options:
                for value in execution_environment.runtime_container_options:
                    command.append(f"--container-options={value}")
            command.extend(["--pull-policy", "never"])
            if execution_environment.runtime_environment:
                for k, v in execution_environment.runtime_environment.items():
                    command.extend(["--set-environment-variable", f"{k}={v}"])
            command.extend(["--execution-environment-image", built_image])
            # Note that another parameter must follow after --set-environment-variable
            # to prevent an argument parsing SNAFU by ansible-navigator.
            # Otherwise you get errors such as "Error: The following set-environment-variable
            # entry could not be parsed: tests/ee/all.yml"...
            command.extend(
                [
                    "-v",
                    playbook,
                ]
            )
            if execution_environment.runtime_extra_vars:
                for k, v in execution_environment.runtime_extra_vars.items():
                    command.extend(["-e", f"{k}={v}"])
            session.run(
                *command,
                env=env,
            )

    # Get container engine preference to check for valid values
    get_container_engine_preference()

    session_func.__doc__ = (
        "Build and test execution environment image:"
        f" {execution_environment.description}"
    )
    nox.session(name=session_name, default=default)(session_func)

    data = {
        "name": session_name,
        "description": execution_environment.description,
        "tags": ["ee", "docker"],
    }
    register("execution-environment", data)


def add_execution_environment_sessions(
    *,
    execution_environments: list[ExecutionEnvironmentData],
    default: bool = False,
    ansible_builder_package: PackageTypeOrList = "ansible-builder",
    ansible_core_package: PackageTypeOrList | None = None,
    ansible_navigator_package: PackageTypeOrList = "ansible-navigator",
) -> None:
    """
    Build and test execution environments for the collection.
    """

    session_names = []
    for ee in execution_environments:
        session_name = f"ee-check-{ee.name}"
        add_execution_environment_session(
            session_name=session_name,
            execution_environment=ee,
            default=False,
            ansible_builder_package=ansible_builder_package,
            ansible_core_package=ansible_core_package,
            ansible_navigator_package=ansible_navigator_package,
        )
        session_names.append(session_name)

    def session_func(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        pass

    session_func.__doc__ = (
        "Meta session for building and testing execution environment images"
    )
    nox.session(
        name="ee-check",
        requires=session_names,
        default=default,
    )(session_func)
