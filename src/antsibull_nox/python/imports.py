# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Python utilities for import relations.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import typing as t
from pathlib import Path

if t.TYPE_CHECKING:
    from collections.abc import Sequence


@dataclasses.dataclass(eq=True, frozen=True)
class PythonModule:
    """
    A Python module.
    """

    path: Path
    module_path: tuple[str, ...]
    imports: frozenset[PythonImport]
    parsable: bool


@dataclasses.dataclass(eq=True, frozen=True)
class PythonImport:
    """
    A symbol import in a Python module.
    """

    symbol_path: tuple[str, ...]

    def belongs_to(self, module_path: tuple[str, ...]) -> bool:
        """
        Determine whether the imported symbol is part of the module.
        """
        return module_path == self.symbol_path[: len(module_path)]


class ImportFinder(ast.NodeVisitor):
    """Visitor for finding all imports."""

    def __init__(self, module_path: tuple[str, ...]) -> None:
        """
        Create import finder for a module of given path.
        """
        self.module_path = list(module_path)
        self.imports: set[PythonImport] = set()
        self.imports_ok = True

    def visit_Import(self, node: ast.Import) -> None:  # pylint: disable=invalid-name
        """Visit an 'import' node."""
        self.generic_visit(node)
        for alias in node.names:
            self.imports.add(PythonImport(tuple(alias.name.split("."))))

    def visit_ImportFrom(  # pylint: disable=invalid-name
        self, node: ast.ImportFrom
    ) -> None:
        """Visit an 'import from' node."""
        self.generic_visit(node)
        base = node.module.split(".") if node.module else []
        if node.level > 0:
            if node.level > len(self.module_path):
                self.imports_ok = False
                return
            base = self.module_path[: -node.level] + base
        base.append("")
        for alias in node.names:
            base[-1] = alias.name
            self.imports.add(PythonImport(tuple(base)))


def get_imported_packages(
    path: Path, module_path: tuple[str, ...]
) -> tuple[set[PythonImport], bool]:
    """
    Load all Python imports from a Python file.
    """
    with path.open("rb") as f:
        contents = f.read()

    try:
        tree = ast.parse(contents)
    except SyntaxError:
        return set(), False

    finder = ImportFinder(module_path)
    finder.visit(tree)
    return finder.imports, finder.imports_ok


def get_module_data_from_module_path(
    path: Path, *, module_path: tuple[str, ...]
) -> PythonModule:
    """
    Given a Python file and a source root, load the module information.
    """
    imports, parsable = get_imported_packages(path, module_path)
    return PythonModule(
        path=path,
        module_path=module_path,
        imports=frozenset(imports),
        parsable=parsable,
    )


def get_module_path(relative_path: Path) -> tuple[str, ...]:
    """
    Given a relative path to a Python file form the source root, extract the module's path.
    """
    module_path = tuple(
        parent.name for parent in reversed(tuple(relative_path.parents)[:-1])
    )
    if relative_path.name == "__init__.py":
        return module_path
    return module_path + (relative_path.name.removesuffix(".py"),)


def get_module_data_from_source_root(path: Path, *, source_root: Path) -> PythonModule:
    """
    Given a Python file and a source root, load the module information.
    """
    relative_path = path.resolve().relative_to(source_root.resolve())
    module_path = get_module_path(relative_path)
    return get_module_data_from_module_path(path, module_path=module_path)


def get_all_module_data(
    paths_with_module_paths: Sequence[tuple[Path, tuple[str, ...]]],
) -> t.Generator[PythonModule]:
    """
    Given a source root and a sequence of paths in it,
    load information on all Python files in these paths.
    """
    for path, module_path in paths_with_module_paths:
        resolved_path = path.resolve()
        if resolved_path.is_dir():
            for dirpath, _, filenames in os.walk(path):
                reldir = Path(dirpath).relative_to(path)
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    rel_module_path = get_module_path(reldir / filename)
                    file_path = Path(dirpath) / filename
                    yield get_module_data_from_module_path(
                        file_path, module_path=module_path + rel_module_path
                    )
        elif resolved_path.is_file():
            yield get_module_data_from_module_path(path, module_path=module_path)


__all__ = (
    "get_all_module_data",
    "get_imported_packages",
    "get_module_data_from_module_path",
    "get_module_data_from_source_root",
    "get_module_path",
)
