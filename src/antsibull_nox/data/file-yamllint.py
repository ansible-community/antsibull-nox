#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make sure all plugin and module documentation adheres to yamllint."""

from __future__ import annotations

import io
import os
import sys
import traceback
import typing as t

from antsibull_nox_data_util import setup  # type: ignore
from yamllint import linter
from yamllint.cli import find_project_config_filepath
from yamllint.config import YamlLintConfig
from yamllint.linter import PROBLEM_LEVELS

REPORT_LEVELS: set[PROBLEM_LEVELS] = {
    "warning",
    "error",
}


def lint(
    *,
    errors: list[dict[str, t.Any]],
    path: str,
    data: str,
    config: YamlLintConfig,
) -> None:
    try:
        problems = linter.run(
            io.StringIO(data),
            config,
            path,
        )
        for problem in problems:
            if problem.level not in REPORT_LEVELS:
                continue
            msg = f"{problem.level}: {problem.desc}"
            if problem.rule:
                msg += f"  ({problem.rule})"
            errors.append(
                {
                    "path": path,
                    "line": problem.line,
                    "col": problem.column,
                    "message": msg,
                }
            )
    except Exception as exc:
        error = str(exc).replace("\n", " / ")
        errors.append(
            {
                "path": path,
                "line": 1,
                "col": 1,
                "message": (
                    f"Internal error while linting YAML: exception {type(exc)}:"
                    f" {error}; traceback: {traceback.format_exc()!r}"
                ),
            }
        )


def process_yaml_file(
    errors: list[dict[str, t.Any]],
    path: str,
    config: YamlLintConfig,
) -> None:
    try:
        with open(path, "rt", encoding="utf-8") as stream:
            data = stream.read()
    except Exception as exc:
        errors.append(
            {
                "path": path,
                "line": 1,
                "col": 1,
                "message": (
                    f"Error while parsing Python code: exception {type(exc)}:"
                    f" {exc}; traceback: {traceback.format_exc()!r}"
                ),
            }
        )
        return

    lint(
        errors=errors,
        path=path,
        data=data,
        config=config,
    )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()
    config: str | None = extra_data.get("config")

    if config is None:
        config = find_project_config_filepath()

    if config:
        yamllint_config = YamlLintConfig(file=config)
    else:
        yamllint_config = YamlLintConfig(content="extends: default")

    errors: list[dict[str, t.Any]] = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        process_yaml_file(errors, path, yamllint_config)

    errors.sort(
        key=lambda error: (error["path"], error["line"], error["col"], error["message"])
    )
    for error in errors:
        prefix = f"{error['path']}:{error['line']}:{error['col']}: "
        msg = error["message"]
        if "note" in error:
            msg = f"{msg}\nNote: {error['note']}"
        for i, line in enumerate(msg.splitlines()):
            print(f"{prefix}{line}")
            if i == 0:
                prefix = " " * len(prefix)

    return len(errors) > 0


if __name__ == "__main__":
    sys.exit(main())
