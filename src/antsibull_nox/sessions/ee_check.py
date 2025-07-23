# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Build execution environments for testing.
"""

from __future__ import annotations

import os
import shutil
import typing as t
from dataclasses import dataclass
from pathlib import Path

import nox

from antsibull_nox.ee_config import generate_ee_config
from antsibull_nox.paths import create_temp_directory

from ..collection import CollectionData, build_collection
from .utils import install, register


@dataclass
class ExecutionEnvironmentData:
    """
    Information for an execution environment session.
    """

    name: str
    description: str
    config: dict[str, t.Any]
    test_playbooks: list[str]


EXAMPLE_EE_DATA_1 = ExecutionEnvironmentData(
    name="devel-ubi-9",
    description="ansible-core devel @ RHEL UBI 9",
    config={
        "version": 3,
        "images": {
            "base_image": {
                "name": "docker.io/redhat/ubi9:latest",
            },
        },
        "dependencies": {
            "ansible_core": {
                "package_pip": "https://github.com/ansible/ansible/archive/devel.tar.gz",
            },
            "ansible_runner": {
                "package_pip": "ansible-runner",
            },
            "python_interpreter": {
                "package_system": "python3.11 python3.11-pip "
                "python3.11-wheel python3.11-cryptography",
                "python_path": "/usr/bin/python3.11",
            },
        },
    },
    test_playbooks=["tests/ee/all.yml"],
)

EXAMPLE_EE_DATA_2 = ExecutionEnvironmentData(
    name="2.15-rocky-9",
    description="ansible-core 2.15 @ Rocky Linux 9",
    config={
        "version": 3,
        "images": {
            "base_image": {
                "name": "quay.io/rockylinux/rockylinux:9",
            },
        },
        "dependencies": {
            "ansible_core": {
                "package_pip": "https://github.com/ansible/ansible/archive/stable-2.15.tar.gz",
            },
            "ansible_runner": {
                "package_pip": "ansible-runner",
            },
        },
    },
    test_playbooks=["tests/ee/all.yml"],
)


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
    container_engine: str,
    default: bool = False,
) -> None:
    """
    Build and test execution environments for the collection.
    """

    def session_func(session: nox.Session):
        install(session, "ansible-builder", "ansible-navigator")

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
            playbook_path = playbook_dir / playbook
            env = {"TMPDIR": str(temp_dir)}
            session.run(
                "ansible-navigator",
                "run",
                "--mode",
                "stdout",
                "--container-engine",
                container_engine,
                "--pull-policy",
                "never",
                "--execution-environment-image",
                built_image,
                "-v",
                playbook,
                env=env,
            )

    session_func.__doc__ = (
        "Build and test execution environment image:"
        f" {execution_environment.description}"
        f" using {container_engine}"
    )
    nox.session(name=session_name, default=default)(session_func)

    data = {
        "name": session_name,
        "description": f"{execution_environment.description} ({container_engine})",
    }
    register("execution-environment", data)


def add_execution_environment_sessions(
    *,
    execution_environments: list[ExecutionEnvironmentData],
    default: bool = False,
) -> None:
    """
    Build and test execution environments for the collection.
    """

    container_engine = os.environ.get("ANTSIBULL_NOX_CONTAINER_ENGINE", "docker")

    session_names = []
    for ee in execution_environments:
        session_name = f"ee-check-{ee.name}"
        add_execution_environment_session(
            session_name=session_name,
            execution_environment=ee,
            container_engine=container_engine,
            default=False,
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
