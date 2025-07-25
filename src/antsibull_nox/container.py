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
import typing as t

ContainerEngineType = t.Literal["docker", "podman"]
ContainerEnginePreferenceType = t.Literal[
    "docker", "podman", "auto", "auto-prefer-docker", "auto-prefer-podman"
]

ANTSIBULL_NOX_CONTAINER_ENGINE = "ANTSIBULL_NOX_CONTAINER_ENGINE"
VALID_CONTAINER_ENGINE_PREFERENCES = {
    "docker",
    "podman",
    "auto",
    "auto-prefer-docker",
    "auto-prefer-podman",
}
DEFAULT_CONTAINER_ENGINE_PREFERENCE = "auto"


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


@functools.cache
def get_preferred_container_engine() -> ContainerEngineType:
    """
    Get the name of the preferred container engine.
    """
    preference = get_container_engine_preference()[0]
    if preference in ("podman", "docker"):
        return preference
    # TODO
    return "docker"


__all__ = (
    "get_container_engine_preference",
    "get_preferred_container_engine",
)
