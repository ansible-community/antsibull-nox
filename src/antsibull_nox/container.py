# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Container engine related tools
"""

from __future__ import annotations

import functools
import os
import shutil
import subprocess
import typing as t

ContainerEngineType = t.Literal["docker", "podman"]
ContainerEnginePreferenceType = t.Literal[
    "docker", "podman", "auto", "auto-prefer-docker", "auto-prefer-podman"
]

ANTSIBULL_NOX_CONTAINER_ENGINE = "ANTSIBULL_NOX_CONTAINER_ENGINE"
VALID_CONTAINER_ENGINE_PREFERENCES: set[ContainerEnginePreferenceType] = {
    "docker",
    "podman",
    "auto",
    "auto-prefer-docker",
    "auto-prefer-podman",
}
DEFAULT_CONTAINER_ENGINE_PREFERENCE: ContainerEnginePreferenceType = "auto"


@functools.cache
def get_container_engine_preference() -> tuple[ContainerEnginePreferenceType, bool]:
    """
    Get the container engine preference.
    """
    container_engine = os.environ.get(ANTSIBULL_NOX_CONTAINER_ENGINE)
    if not container_engine:
        return DEFAULT_CONTAINER_ENGINE_PREFERENCE, False
    if container_engine not in VALID_CONTAINER_ENGINE_PREFERENCES:
        allowed_values = ", ".join(sorted(VALID_CONTAINER_ENGINE_PREFERENCES))
        raise ValueError(
            f"Invalid value for {ANTSIBULL_NOX_CONTAINER_ENGINE}: {container_engine!r}."
            f" Expected one of: {allowed_values}"
        )
    return t.cast(ContainerEnginePreferenceType, container_engine), True


def _get_version(exec_path: str) -> str | None:
    try:
        completed = subprocess.run(
            [exec_path, "-v"], capture_output=True, check=True, encoding="utf-8"
        )
        return completed.stdout.strip()
    except Exception:  # pylint: disable=broad-exception-caught
        return None


@functools.cache
def get_preferred_container_engine() -> ContainerEngineType:
    """
    Get the name of the preferred container engine.
    """
    preference = get_container_engine_preference()[0]
    if preference in ("podman", "docker"):
        return t.cast(ContainerEngineType, preference)
    docker_path = shutil.which("docker")
    podman_path = shutil.which("podman")
    if podman_path:
        version = _get_version(podman_path)
        if version is None:
            podman_path = None
    if docker_path:
        version = _get_version(docker_path)
        if version is None:
            docker_path = None
        elif "podman" in version and podman_path is not None:
            docker_path = None
    print(preference, docker_path, podman_path)
    if docker_path and podman_path:
        # Prefer one over the other by user's preference
        if preference == "auto-prefer-docker":
            podman_path = None
        if preference == "auto-prefer-podman":
            docker_path = None
    # Pick one
    if docker_path:
        return "docker"
    if podman_path:
        return "podman"
    raise ValueError("Could neither find 'docker' or 'podman' CLI on path!")


__all__ = (
    "get_container_engine_preference",
    "get_preferred_container_engine",
)
