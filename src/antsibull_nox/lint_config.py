# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""Lint antsibull-nox config."""

from __future__ import annotations

import ast
from pathlib import Path

from .config import lint_config_toml

NOXFILE_PY = "noxfile.py"


def _is_antsibull_nox_module(module_name: str) -> bool:
    return module_name == "antsibull_nox" or module_name.startswith("antsibull_nox.")


class _Walker:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.imports: dict[str, str] = {}
        self.has_config_load = False

    @staticmethod
    def _get_name(what: ast.expr) -> str | None:
        if isinstance(what, ast.Name):
            return what.id
        if isinstance(what, ast.Attribute):
            v = _Walker._get_name(what.value)
            return None if v is None else f"{v}.{what.attr}"
        return None

    def _check_expression(self, expression: ast.expr) -> None:
        if isinstance(expression, ast.Call):
            func = _Walker._get_name(expression.func)
            if func is not None:
                func = self.imports.get(func, func)
                if "." in func:
                    module, module_func = func.rsplit(".", 1)
                    if module in self.imports:
                        func = f"{self.imports[module]}.{module_func}"
                if func == "antsibull_nox.load_antsibull_nox_toml":
                    self.has_config_load = True

    def _walk(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            # Handle imports
            if isinstance(statement, ast.Import):
                for alias in statement.names:
                    if _is_antsibull_nox_module(alias.name):
                        self.imports[alias.asname or alias.name] = alias.name
            if isinstance(statement, ast.ImportFrom):
                if statement.level == 0 and _is_antsibull_nox_module(
                    statement.module or ""
                ):
                    for alias in statement.names:
                        self.imports[alias.asname or alias.name] = (
                            f"{statement.module}.{alias.name}"
                        )
            # Handle try block
            if isinstance(statement, ast.Try):
                self._walk(statement.body)
            # Handle expressions
            if isinstance(statement, ast.Expr):
                self._check_expression(statement.value)

    def walk(self, module: ast.Module) -> list[str]:
        """
        Walk the noxfile's module and return a list of errors.
        """
        self._walk(module.body)
        errors = []
        if not self.imports:
            errors.append(f"{self.path}: Found no antsibull_nox import")
        if not self.has_config_load:
            errors.append(
                f"{self.path}: Found no call to antsibull_nox.load_antsibull_nox_toml()"
            )
        return errors


def lint_noxfile() -> list[str]:
    """
    Do basic validation for noxfile.py. Return a list of errors.
    """
    path = Path(NOXFILE_PY)
    try:
        with open(path, "rt", encoding="utf-8") as f:
            root = ast.parse(f.read(), filename=path)
    except FileNotFoundError:
        return [f"{path}: File does not exist"]
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [f"{path}:Error while parsing Python code: {exc}"]

    walker = _Walker(path)
    return walker.walk(root)


def lint_config() -> list[str]:
    """
    Lint antsibull-nox config file.
    """
    errors = lint_config_toml()
    errors.extend(lint_noxfile())
    return sorted(errors)


__all__ = ["lint_config"]
