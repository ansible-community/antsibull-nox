# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Execution environment definition generator.
"""

from __future__ import annotations

import typing as t
from copy import deepcopy
from pathlib import Path

from antsibull_fileutils.yaml import store_yaml_file

from .collection import CollectionData


def find_dict(destination: dict[str, t.Any], path: list[str]) -> dict[str, t.Any]:
    """
    Find/create dictionary determined by ``path`` in ``destination``.
    """
    for index, key in enumerate(path):
        if key not in destination:
            destination[key] = {}
        if not isinstance(destination[key], dict):
            raise ValueError(
                f"Expected a dictionary at {'.'.join(path[:index + 1])},"
                f" but found {type(destination[key])}"
            )
        destination = destination[key]
    return destination


def set_value(destination: dict[str, t.Any], path: list[str], value: t.Any) -> None:
    """
    Set value determined by ``path`` in ``destination`` to ``value``.
    """
    find_dict(destination, path[:-1])[path[-1]] = value


def generate_ee_config(
    *,
    directory: Path,
    collection_tarball_path: Path,
    collection_data: CollectionData,  # pylint: disable=unused-argument
    ee_config: dict[str, t.Any],
) -> None:
    """
    Create execution environment definition.
    """
    config = deepcopy(ee_config)

    # Add Galaxy requirements file
    store_yaml_file(
        directory / "requirements.yml",
        {
            "collections": [
                {
                    "name": f"src/{collection_tarball_path.name}",
                    "type": "file",
                },
            ],
        },
    )
    set_value(config, ["dependencies", "galaxy"], "requirements.yml")

    # Add collection
    if "additional_build_files" not in config:
        config["additional_build_files"] = []
    if not isinstance(config["additional_build_files"], list):
        raise ValueError(
            f"Expected a list at additional_build_files,"
            f" but found {type(config['additional_build_files'])}"
        )
    config["additional_build_files"].append(
        {
            "src": str(collection_tarball_path),
            "dest": "src",
        }
    )

    store_yaml_file(directory / "execution-environment.yml", config)


def create_ee_config(
    version: int = 3,
    base_image: str | None = None,
    dependencies: dict[str, t.Any] | None = None,
) -> dict[str, t.Any]:
    """
    Create execution environment from parameters.
    """

    config: dict[str, t.Any] = {
        "version": version,
        "images": {
            "base_image": {
                "name": base_image or "registry.fedoraproject.org/fedora-toolbox:latest"
            }
        },
        "dependencies": dependencies or {},
    }

    return config


__all__ = ["generate_ee_config", "create_ee_config"]
