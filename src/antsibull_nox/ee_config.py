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

ALLOWED_EE_DEFINITION_VERSIONS = {3}


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

    if config.get("version") not in ALLOWED_EE_DEFINITION_VERSIONS:
        raise ValueError(f"Invalid EE definition version {config.get('version')!r}")

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


def merge(
    destination: dict[str, t.Any],
    source: dict[str, t.Any],
    *,
    path: list[str] | None = None,
    ok_paths: list[list[str]] | None = None,
    source_name: str,
) -> None:
    """
    Given two EE configs, merge the second into the first.

    In case values are specified in both configs, an error is reported.
    """
    if path is None:
        path = []
    for k, v in source.items():
        if destination.get(k) is None:
            destination[k] = v
            continue
        sub_path = path + [k]
        if not isinstance(destination[k], dict) or not isinstance(v, dict):
            if ok_paths and sub_path in ok_paths:
                destination[k] = v
                continue
            raise ValueError(
                f"Value {'.'.join(sub_path)} is already present"
                f" in the EE config (type {type(destination[k])});"
                f" cannot overwrite with value (type {type(source[k])}) from {source_name}"
            )
        merge(
            destination[k],
            source[k],
            path=sub_path,
            source_name=source_name,
            ok_paths=ok_paths,
        )


def create_ee_config(
    *,
    version: t.Literal[3],
    base_image: str | None = None,
    base_image_is_default: bool = False,
    dependencies: dict[str, t.Any] | None = None,
    config: dict[str, t.Any] | None = None,
) -> dict[str, t.Any]:
    """
    Create execution environment from parameters.
    """

    if version not in ALLOWED_EE_DEFINITION_VERSIONS:
        raise ValueError(f"Invalid EE definition version {version!r}")

    final_config: dict[str, t.Any] = {}

    # Merge session parameters
    parameter_config: dict[str, t.Any] = {
        "version": version,
    }
    if base_image is not None:
        parameter_config["images"] = {"base_image": {"name": base_image}}
    if dependencies:
        parameter_config["dependencies"] = dependencies
    merge(final_config, parameter_config, path=[], source_name="session parameters")

    # Merge passed config
    if config:
        merge(
            final_config,
            config,
            source_name="config",
            ok_paths=(
                [["images", "base_image"], ["images", "base_image", "name"]]
                if base_image_is_default
                else []
            ),
        )

    return final_config


__all__ = ["generate_ee_config", "create_ee_config"]
