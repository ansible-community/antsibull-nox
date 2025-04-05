# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Ansible-core version utilities.
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass

from .utils import Version


@dataclass(frozen=True)
class AnsibleCoreInfo:
    """
    Information on an ansible-core version.
    """

    ansible_core_version: Version
    controller_python_versions: tuple[Version, ...]
    remote_python_versions: tuple[Version, ...]


_SUPPORTED_CORE_VERSIONS: dict[Version, AnsibleCoreInfo] = {
    Version.parse(ansible_version): AnsibleCoreInfo(
        ansible_core_version=Version.parse(ansible_version),
        controller_python_versions=tuple(
            Version.parse(v) for v in controller_python_versions
        ),
        remote_python_versions=tuple(Version.parse(v) for v in remote_python_versions),
    )
    for ansible_version, (controller_python_versions, remote_python_versions) in {
        "2.9": [
            ["2.7", "3.5", "3.6", "3.7", "3.8"],
            ["2.6", "2.7", "3.5", "3.6", "3.7", "3.8"],
        ],
        "2.10": [
            ["2.7", "3.5", "3.6", "3.7", "3.8", "3.9"],
            ["2.6", "2.7", "3.5", "3.6", "3.7", "3.8", "3.9"],
        ],
        "2.11": [
            ["2.7", "3.5", "3.6", "3.7", "3.8", "3.9"],
            ["2.6", "2.7", "3.5", "3.6", "3.7", "3.8", "3.9"],
        ],
        "2.12": [
            ["3.8", "3.9", "3.10"],
            ["2.6", "2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10"],
        ],
        "2.13": [
            ["3.8", "3.9", "3.10"],
            ["2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10"],
        ],
        "2.14": [
            ["3.9", "3.10", "3.11"],
            ["2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11"],
        ],
        "2.15": [
            ["3.9", "3.10", "3.11"],
            ["2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11"],
        ],
        "2.16": [
            ["3.10", "3.11", "3.12"],
            ["2.7", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12"],
        ],
        "2.17": [
            ["3.10", "3.11", "3.12"],
            ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"],
        ],
        "2.18": [
            ["3.11", "3.12", "3.13"],
            ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"],
        ],
        "2.19": [
            ["3.11", "3.12", "3.13"],
            ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"],
        ],
        # The following might need updates. Look for the "``ansible-core`` support matrix" table in:
        # https://github.com/ansible/ansible-documentation/blob/devel/docs/docsite/rst/reference_appendices/release_and_maintenance.rst?plain=1
        # It contains commented-out entries for future ansible-core versions.
        "2.20": [
            ["3.12", "3.13", "3.14"],
            ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"],
        ],
        "2.21": [
            ["3.12", "3.13", "3.14"],
            ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"],
        ],
        "2.22": [
            ["3.13", "3.14", "3.15"],
            ["3.10", "3.11", "3.12", "3.13", "3.14", "3.15"],
        ],
        "2.23": [
            ["3.13", "3.14", "3.15"],
            ["3.10", "3.11", "3.12", "3.13", "3.14", "3.15"],
        ],
        "2.24": [
            ["3.14", "3.15", "3.16"],
            ["3.11", "3.12", "3.13", "3.14", "3.15", "3.16"],
        ],
        "2.25": [
            ["3.14", "3.15", "3.16"],
            ["3.11", "3.12", "3.13", "3.14", "3.15", "3.16"],
        ],
    }.items()
}

_CURRENT_DEVEL_VERSION = Version.parse("2.19")
_CURRENT_MILESTONE_VERSION = Version.parse("2.19")


def get_ansible_core_info(
    core_version: Version | t.Literal["devel", "milestone"],
) -> AnsibleCoreInfo:
    """
    Retrieve information on an ansible-core version.
    """
    version: Version
    if core_version == "devel":
        version = _CURRENT_DEVEL_VERSION
    elif core_version == "milestone":
        version = _CURRENT_MILESTONE_VERSION
    else:
        version = core_version
    if version in _SUPPORTED_CORE_VERSIONS:
        return _SUPPORTED_CORE_VERSIONS[version]
    raise ValueError(f"Unknown ansible-core version {version}")


__all__ = [
    "AnsibleCoreInfo",
    "get_ansible_core_info",
]
