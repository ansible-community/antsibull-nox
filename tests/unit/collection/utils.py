# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

"""
Tests for the collection module
"""

from __future__ import annotations

import typing as t
from pathlib import Path

from antsibull_fileutils.yaml import store_yaml_file

from antsibull_nox.collection.install import (
    Runner,
)


def create_collection(
    path: Path,
    *,
    namespace: str,
    name: str,
    version: str | None = None,
    dependencies: dict[str, str] | None = None,
) -> None:
    data: dict[str, t.Any] = {
        "namespace": namespace,
        "name": name,
    }
    if version is not None:
        data["version"] = version
    if dependencies is not None:
        data["dependencies"] = dependencies
    path.mkdir(parents=True, exist_ok=True)
    store_yaml_file(path / "galaxy.yml", data)


def create_collection_w_dir(
    root: Path,
    *,
    namespace: str,
    name: str,
    version: str | None = None,
    dependencies: dict[str, str] | None = None,
) -> Path:
    path = root / namespace / name
    create_collection(
        path=path,
        namespace=namespace,
        name=name,
        version=version,
        dependencies=dependencies,
    )
    return path


def create_collection_w_shallow_dir(
    root: Path,
    *,
    directory_override: str | None = None,
    namespace: str,
    name: str,
    version: str | None = None,
    dependencies: dict[str, str] | None = None,
) -> Path:
    path = root / (directory_override or f"{namespace}.{name}")
    create_collection(
        path=path,
        namespace=namespace,
        name=name,
        version=version,
        dependencies=dependencies,
    )
    return path


def create_once_runner(args: list[str], stdout: bytes, stderr: bytes = b"") -> Runner:
    call_counter = [0]

    def runner(call_args: list[str]) -> tuple[bytes, bytes]:
        assert call_counter[0] == 0
        assert call_args == args
        call_counter[0] += 1
        return stdout, stderr

    return runner
