# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Build execution environments for testing.
"""

from __future__ import annotations

import subprocess
import typing as t
from dataclasses import dataclass
from pathlib import Path

import nox

from antsibull_nox.ee_config_generator import ExecutionEnvironmentGenerator

from ..collection import CollectionData, build_collection
from .utils import register


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


def build_ee_image(collection_path: Path, namespace: str, name: str) -> list[str]:
    """
    Build container images for execution environments.

    Args:
        collection_path: Path to directory that contains execution environment definitions
        namespace: Collection namespace
        name: Collection

    Returns:
        List of successfully built container image names
    """
    built_images = []

    ee_files = list(collection_path.glob("execution-environment-*.yml"))

    for ee_file in ee_files:
        prefix = "execution-environment-"
        image_name = f"{namespace}-{name}-{ee_file.stem.replace(prefix, '')}"

        try:
            context_dir = str(ee_file.parent / f"context-{ee_file.stem}")

            cmd = [
                "ansible-builder",
                "build",
                "--file",
                str(ee_file),
                "--tag",
                image_name,
                "--container-runtime",
                "podman",
                "--verbosity",
                "3",
                "--context",
                context_dir,
            ]

            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            if result.returncode == 0:
                built_images.append(image_name)
            else:
                print(
                    f"Could not build image for {ee_file}, return code: {result.returncode}"
                )

        except OSError as e:
            print(
                f"An error was encountered while building an image for {ee_file}: {e}"
            )

    return built_images


def prepare_execution_environment(
    *,
    session: nox.Session,
    execution_environment: ExecutionEnvironmentData,
) -> tuple[Path, list[str], CollectionData]:
    """
    Generate execution environments for a collection.

    Args:
        session: Nox session object

    Returns:
        Tuple with:
        - collection_tarball_path: Path to the built collection tarball
        - built_image_names: List of built container images
        - collection_data: Collection metadata
    """
    collection_tarball_result = build_collection(session)

    collection_tarball_path = collection_tarball_result[0]
    if collection_tarball_path is None:
        raise RuntimeError("Failed to build collection tarball")

    collection_data = collection_tarball_result[1]

    tmp = Path(session.create_tmp())

    ee_generator = ExecutionEnvironmentGenerator()
    ee_generator.generate_requirements_file(tmp, collection_tarball_path.name)
    ee_generator.generate_execution_environments(tmp, collection_tarball_path.name)

    built_images = build_ee_image(tmp, collection_data.namespace, collection_data.name)

    return collection_tarball_path, built_images, collection_data


def add_execution_environment_session(
    *,
    session_name: str,
    execution_environment: ExecutionEnvironmentData,
    default: bool = False,
) -> None:
    """
    Build and test execution environments for the collection.
    """

    def session_func(session: nox.Session):
        collection_tarball, built_images, collection_data = (
            prepare_execution_environment(
                session=session, execution_environment=execution_environment
            )
        )

        session.log(
            f"Building execution environment {execution_environment.description}"
            f" for {collection_data.namespace}.{collection_data.name}"
        )

        if built_images:
            session.log(f"Successfully built images: {', '.join(built_images)}")
        else:
            session.warn("No execution environment images were built")

        session.log(f"Collection tarball: {collection_tarball}")

        # TODO: run ee tests (playbooks from execution_environment.test_playbooks)

    session_func.__doc__ = (
        "Build and test execution environment image:"
        f" {execution_environment.description}"
    )
    nox.session(name=session_name, default=default)(session_func)

    data = {
        "name": session_name,
        "description": execution_environment.description,
    }
    register("execution-environment", data)


def add_execution_environment_sessions(
    *, execution_environments: list[ExecutionEnvironmentData], default: bool = False
) -> None:
    """
    Build and test execution environments for the collection.
    """
    session_names = []
    for ee in execution_environments:
        session_name = f"ee-check-{ee.name}"
        add_execution_environment_session(
            session_name=session_name, execution_environment=ee, default=False
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
