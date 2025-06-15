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

from antsibull_docutils.rst_code_finder import find_code_blocks
from antsibull_nox_data_util import setup  # type: ignore
from yamllint import linter
from yamllint.config import YamlLintConfig
from yamllint.linter import PROBLEM_LEVELS

REPORT_LEVELS: set[PROBLEM_LEVELS] = {
    "warning",
    "error",
}

YAML_LANGUAGES = {"yaml", "yaml+jinja"}


def lint(
    *,
    errors: list[dict[str, t.Any]],
    path: str,
    data: str,
    row_offset: int,
    col_offset: int,
    config: YamlLintConfig,
    extra_for_errors: dict[str, t.Any] | None = None,
) -> None:
    # If the string start with optional whitespace + linebreak, skip that line
    idx = data.find("\n")
    if idx >= 0 and (idx == 0 or data[:idx].isspace()):
        data = data[idx + 1 :]
        row_offset += 1
        col_offset = 0

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
                    "line": row_offset + problem.line,
                    # The col_offset is only valid for line 1; otherwise the offset is 0
                    "col": (col_offset if problem.line == 1 else 0) + problem.column,
                    "message": msg,
                }
            )
            if extra_for_errors:
                errors[-1].update(extra_for_errors)
    except Exception as exc:
        error = str(exc).replace("\n", " / ")
        errors.append(
            {
                "path": path,
                "line": row_offset + 1,
                "col": col_offset + 1,
                "message": (
                    f"Internal error while linting YAML: exception {type(exc)}:"
                    f" {error}; traceback: {traceback.format_exc()!r}"
                ),
            }
        )
        if extra_for_errors:
            errors[-1].update(extra_for_errors)


def process_rst_file(
    errors: list[dict[str, t.Any]],
    path: str,
    config: YamlLintConfig,
) -> None:
    try:
        with open(path, "rt", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        errors.append(
            {
                "path": path,
                "line": 1,
                "col": 1,
                "message": (
                    f"Error while reading content: {type(exc)}:"
                    f" {exc}; traceback: {traceback.format_exc()!r}"
                ),
            }
        )
        return

    def warn_unknown_block(line: int | str, col: int, content: str) -> None:
        errors.append(
            {
                "path": path,
                "line": line,
                "col": col,
                "message": (
                    "Warning: found unknown literal block! Check for double colons '::'."
                    " If that is not the cause, please report this warning."
                    " It might indicate a bug in the checker or an unsupported Sphinx directive."
                    f" Content: {content!r}"
                ),
            }
        )

    for code_block in find_code_blocks(
        content,
        path=path,
        root_prefix="docs/docsite/rst",
        warn_unknown_block=warn_unknown_block,
    ):
        if (code_block.language or "").lower() not in YAML_LANGUAGES:
            continue

        extra_for_errors = {}
        if not code_block.position_exact:
            extra_for_errors["note"] = (
                "The code block could not be exactly located in the source file."
                " The line/column numbers might be off."
            )

        # Parse the (remaining) string content
        lint(
            errors=errors,
            path=path,
            data=code_block.content,
            row_offset=code_block.row_offset,
            col_offset=code_block.col_offset,
            config=config,
            extra_for_errors=extra_for_errors,
        )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()
    config: str | None = extra_data.get("config")

    if config:
        yamllint_config = YamlLintConfig(file=config)
    else:
        yamllint_config = YamlLintConfig(content="extends: default")

    errors: list[dict[str, t.Any]] = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        process_rst_file(errors, path, yamllint_config)

    errors.sort(
        key=lambda error: (
            error["path"],
            error["line"] if isinstance(error["line"], int) else 0,
            error["col"],
            error["message"],
        )
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
