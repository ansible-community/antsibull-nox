# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Python file dependency data.
"""

from __future__ import annotations

import functools
import typing as t
from dataclasses import dataclass
from pathlib import Path

from ..collection import load_collection_data_from_disk
from ..paths import list_all_files
from .imports import PythonModule, get_module_data_from_module_path, get_module_path


@dataclass
class PythonDependencyInfo:
    """
    Stores Python dependency information.
    """

    file_to_module_path: dict[Path, tuple[str, ...]]
    module_path_to_file: dict[tuple[str, ...], Path]
    file_to_imported_modules: dict[
        Path, tuple[frozenset[tuple[str, ...]], frozenset[Path]]
    ]
    file_to_imported_by_modules: dict[
        Path, tuple[frozenset[tuple[str, ...]], frozenset[Path]]
    ]


@dataclass
class _Node:
    python_module: PythonModule | None
    children: dict[str, _Node]

    def find(
        self, module_path: tuple[str, ...]
    ) -> tuple[PythonModule, tuple[str, ...]] | None:
        """
        Find Python module and remaining path for module path.
        """
        next_node = self.children.get(module_path[0]) if len(module_path) > 0 else None
        if next_node is not None:
            return next_node.find(module_path[1:])
        if self.python_module is None:
            return None
        return self.python_module, module_path

    def add(
        self,
        python_module: PythonModule,
        *,
        relative_path: tuple[str, ...] | None = None,
    ) -> None:
        """
        Add Python module to tree.
        """
        if relative_path is None:
            relative_path = python_module.module_path
        if len(relative_path) == 0:
            if self.python_module is not None:
                raise ValueError(
                    f"Found multiple modules for {relative_path}:"
                    f" {python_module.path} vs. {self.python_module.path}"
                )
            self.python_module = python_module
            return
        next_node = self.children.get(relative_path[0])
        if next_node is None:
            next_node = _Node(None, {})
            self.children[relative_path[0]] = next_node
        next_node.add(python_module, relative_path=relative_path[1:])


def get_all_collection_module_data() -> t.Generator[PythonModule]:
    """
    Load all Python file module infos for the current collection.
    """
    cwd = Path.cwd()
    cd = load_collection_data_from_disk(cwd)
    module_root = ("ansible_collections", cd.namespace, cd.name)
    for path in list_all_files():
        if not path.name.endswith(".py"):
            continue
        module_path = module_root + get_module_path(path.relative_to(cwd))
        yield get_module_data_from_module_path(path, module_path=module_path)


def _get_collection_module_tree() -> tuple[list[PythonModule], _Node]:
    all_modules: list[PythonModule] = []
    root = _Node(None, {})
    for python_module in get_all_collection_module_data():
        all_modules.append(python_module)
        root.add(python_module)
    return all_modules, root


@functools.cache
def get_python_dependency_info() -> PythonDependencyInfo:
    """
    Extract Python dependency information for current collection.
    """
    all_modules, root = _get_collection_module_tree()
    file_to_module_path: dict[Path, tuple[str, ...]] = {}
    module_path_to_file: dict[tuple[str, ...], Path] = {}
    file_to_imported_modules: dict[
        Path, tuple[frozenset[tuple[str, ...]], frozenset[Path]]
    ] = {}
    file_to_imported_by_modules: dict[Path, tuple[set[tuple[str, ...]], set[Path]]] = {}
    for python_module in all_modules:
        file_to_module_path[python_module.path] = python_module.module_path
        module_path_to_file[python_module.module_path] = python_module.path
        file_to_imported_by_modules[python_module.path] = (set(), set())
    for python_module in all_modules:
        module_imports: set[tuple[str, ...]] = set()
        module_import_files: set[Path] = set()
        for python_import in python_module.imports:
            res = root.find(python_import.symbol_path)
            if res is not None:
                module_imports.add(res[0].module_path)
                module_import_files.add(res[0].path)
                imp_by_mp, imp_by_fs = file_to_imported_by_modules[res[0].path]
                imp_by_mp.add(python_module.module_path)
                imp_by_fs.add(python_module.path)
        file_to_imported_modules[python_module.path] = (
            frozenset(module_imports),
            frozenset(module_import_files),
        )
    return PythonDependencyInfo(
        file_to_module_path=file_to_module_path,
        module_path_to_file=module_path_to_file,
        file_to_imported_modules=file_to_imported_modules,
        file_to_imported_by_modules={
            k: (frozenset(v1), frozenset(v2))
            for k, (v1, v2) in file_to_imported_by_modules.items()
        },
    )


__all__ = (
    "PythonDependencyInfo",
    "get_python_dependency_info",
)
