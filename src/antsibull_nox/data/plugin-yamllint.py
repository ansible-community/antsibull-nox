#!/usr/bin/env python

# Copyright (c) 2024, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make sure all plugin and module documentation adheres to yamllint."""

from __future__ import annotations

import ast
import io
import re
import sys
import traceback
import typing as t

from yamllint import linter
from yamllint.config import YamlLintConfig
from yamllint.linter import PROBLEM_LEVELS

from antsibull_nox.data_util import setup

REPORT_LEVELS: set[PROBLEM_LEVELS] = {
    "warning",
    "error",
}

EXAMPLES_FMT_RE = re.compile(r"^# fmt:\s+(\S+)")


def lint(
    *,
    errors: list[dict[str, t.Any]],
    path: str,
    data: str,
    row_offset: int,
    col_offset: int,
    section: str,
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
            msg = f"{section}: {problem.level}: {problem.desc}"
            if problem.rule:
                msg += f"  ({problem.rule})"
            errors.append(
                {
                    "path": path,
                    "line": row_offset + problem.line,
                    # The col_offset is only valid for line 1; otherwise the offset is 0
                    "col": (col_offset if problem.line == 1 else 0) + problem.column,
                    "message": msg,
                }
            )
    except Exception as exc:
        error = str(exc).replace("\n", " / ")
        errors.append(
            {
                "path": path,
                "line": row_offset + 1,
                "col": col_offset + 1,
                "message": (
                    f"{section}: Internal error while linting YAML: exception {type(exc)}:"
                    f" {error}; traceback: {traceback.format_exc()!r}"
                ),
            }
        )


def process_python_file(
    errors: list[dict[str, t.Any]], path: str, config: YamlLintConfig
) -> None:
    try:
        with open(path, "rt", encoding="utf-8") as f:
            root = ast.parse(f.read(), filename=path)
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

    # We look for top-level assignments
    for child in root.body:
        if not isinstance(child, ast.Assign):
            continue
        if not isinstance(child.value, ast.Constant):
            continue
        if not isinstance(child.value.value, str):
            continue
        for target in child.targets:
            try:
                section = target.id  # type: ignore
            except AttributeError:
                continue
            if section not in ("DOCUMENTATION", "EXAMPLES", "RETURN"):
                continue

            # Extract value and offsets
            data = child.value.value
            row_offset = child.value.lineno - 1
            col_offset = child.value.col_offset - 1

            # If the string start with optional whitespace + linebreak, skip that line
            idx = data.find("\n")
            if idx >= 0 and (idx == 0 or data[:idx].isspace()):
                data = data[idx + 1 :]
                row_offset += 1
                col_offset = 0

            # Check for non-YAML examples
            if section == "EXAMPLES":
                fmt_match = EXAMPLES_FMT_RE.match(data.lstrip())
                if fmt_match and fmt_match.group(1) != "yaml":
                    continue

            # Parse the (remaining) string content
            lint(
                errors=errors,
                path=path,
                data=data,
                row_offset=row_offset,
                col_offset=col_offset,
                section=section,
                config=config,
            )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()
    config: str | None = extra_data.get("config")

    if config:
        with open(config, encoding="utf-8") as f:
            yamllint_config = YamlLintConfig(f.read())
    else:
        yamllint_config = YamlLintConfig(content="extends: default")

    errors: list[dict[str, t.Any]] = []
    for path in paths:
        process_python_file(errors, path, yamllint_config)

    errors.sort(
        key=lambda error: (error["path"], error["line"], error["col"], error["message"])
    )
    for error in errors:
        prefix = f"{error['path']}:{error['line']}:{error['col']}: "
        msg = error["message"]
        for i, line in enumerate(msg.splitlines()):
            print(f"{prefix}{line}")
            if i == 0:
                prefix = " " * len(prefix)

    return len(errors) > 0


if __name__ == "__main__":
    sys.exit(main())
