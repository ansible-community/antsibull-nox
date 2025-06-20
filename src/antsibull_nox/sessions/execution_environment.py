# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Build execution environments for testing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from antsibull_nox.ee_config_generator import ExecutionEnvironmentGenerator

from ..collection import CollectionData, build_collection


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
    session, collection_data: CollectionData
) -> tuple[Path, list[str]]:
    """
    Generate execution environments for a collection.

    Args:
        session: Nox session object
        collection_data: Collection metadata

    Returns:
        Tuple with:
        - collection_tarball_path: Path to the built collection tarball
        - built_image_names: List of built container images
    """
    collection_tarball_result = build_collection(session)

    collection_tarball_path = collection_tarball_result[0]
    if collection_tarball_path is None:
        raise RuntimeError("Failed to build collection tarball")

    tmp = Path(session.create_tmp())

    ee_generator = ExecutionEnvironmentGenerator()
    ee_generator.generate_requirements_file(tmp, collection_tarball_path.name)
    ee_generator.generate_execution_environments(tmp, collection_tarball_path.name)

    built_images = build_ee_image(tmp, collection_data.namespace, collection_data.name)

    return collection_tarball_path, built_images


def add_execution_environment_session(
    collection_data: CollectionData,
    session_name: str = "build-ee",
    description: str = "Build execution environment images",
) -> None:
    """
    Creates a nox session that builds execution environments for the collection.

    Args:
        sessions_dict: Dictionary to register the session function
        collection_data: Collection metadata
        session_name: Name for the session
        description: Human-readable description for the session

    Returns:
        None
    """

    def session_func(session):
        session.log(
            f"Building execution environment for {collection_data.namespace}.{collection_data.name}"
        )

        collection_tarball, built_images = prepare_execution_environment(
            session, collection_data
        )

        if built_images:
            session.log(f"Successfully built images: {', '.join(built_images)}")
        else:
            session.warn("No execution environment images were built")

        session.log(f"Collection tarball: {collection_tarball}")

    session_func.__doc__ = description
    sessions_dict[session_name] = session_func
