#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make sure all plugin and module documentation adheres to yamllint."""

from __future__ import annotations

import ast
import io
import os
import re
import sys
import traceback
import typing as t

import yaml
from antsibull_nox_data_util import setup  # type: ignore
from yamllint import linter
from yamllint.config import YamlLintConfig
from yamllint.linter import PROBLEM_LEVELS

REPORT_LEVELS: set[PROBLEM_LEVELS] = {
    "warning",
    "error",
}

EXAMPLES_FMT_RE = re.compile(r"^# fmt:\s+(\S+)")

EXAMPLES_SECTION = "EXAMPLES"


def lint(
    *,
    errors: list[dict[str, t.Any]],
    path: str,
    data: str,
    row_offset: int,
    col_offset: int,
    section: str,
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
                    f"{section}: Internal error while linting YAML: exception {type(exc)}:"
                    f" {error}; traceback: {traceback.format_exc()!r}"
                ),
            }
        )
        if extra_for_errors:
            errors[-1].update(extra_for_errors)


def iterate_targets(
    assignment: ast.Assign,
) -> t.Iterable[tuple[ast.Constant, str, str]]:
    if not isinstance(assignment.value, ast.Constant):
        return
    if not isinstance(assignment.value.value, str):
        return
    for target in assignment.targets:
        try:
            yield assignment.value, assignment.value.value, target.id  # type: ignore
        except AttributeError:
            continue


def process_python_file(
    errors: list[dict[str, t.Any]],
    path: str,
    config: YamlLintConfig,
    config_examples: YamlLintConfig,
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

    is_doc_fragment = path.startswith("plugins/doc_fragments/")

    # We look for top-level assignments and classes
    for child in root.body:
        if (
            is_doc_fragment
            and isinstance(child, ast.ClassDef)
            and child.name == "ModuleDocFragment"
        ):
            for fragment in child.body:
                if not isinstance(fragment, ast.Assign):
                    continue
                for constant, data, fragment_name in iterate_targets(fragment):
                    lint(
                        errors=errors,
                        path=path,
                        data=data,
                        row_offset=constant.lineno - 1,
                        col_offset=constant.col_offset - 1,
                        section=fragment_name,
                        config=config,
                    )
        if not isinstance(child, ast.Assign):
            continue
        for constant, data, section in iterate_targets(child):
            if section not in ("DOCUMENTATION", "EXAMPLES", "RETURN"):
                continue

            # Handle special values
            if data in ("#", " # ") and section == "RETURN":
                # Not skipping it here could result in all kind of linting errors,
                # like no document start, or trailing space.
                continue

            # Check for non-YAML examples
            if section == EXAMPLES_SECTION:
                fmt_match = EXAMPLES_FMT_RE.match(data.lstrip())
                if fmt_match and fmt_match.group(1) != "yaml":
                    continue

            # Parse the (remaining) string content
            lint(
                errors=errors,
                path=path,
                data=data,
                row_offset=constant.lineno - 1,
                col_offset=constant.col_offset - 1,
                section=section,
                config=config_examples if section == EXAMPLES_SECTION else config,
            )


def process_sidecar_docs_file(
    errors: list[dict[str, t.Any]],
    path: str,
    config_examples: YamlLintConfig,
) -> None:
    try:
        # TODO: get hold of YAML structure so we also get correct line/col numbers
        #       inside EXAMPLES!
        with open(path, "rb") as stream:
            root = yaml.load(stream, Loader=yaml.SafeLoader)
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

    if not isinstance(root, dict):
        return
    examples = root.get(EXAMPLES_SECTION)
    if not isinstance(examples, str):
        return

    # Check for non-YAML examples
    fmt_match = EXAMPLES_FMT_RE.match(examples.lstrip())
    if fmt_match and fmt_match.group(1) != "yaml":
        return

    lint(
        errors=errors,
        path=path,
        data=examples,
        row_offset=0,  # TODO
        col_offset=0,  # TODO
        section=EXAMPLES_SECTION,
        config=config_examples,
        extra_for_errors={
            "note": "Line/column are relative to EXAMPLES string contents"
        },
    )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()
    config: str | None = extra_data.get("config")
    config_examples: str | None = extra_data.get("config_examples")

    if config:
        yamllint_config = YamlLintConfig(file=config)
    else:
        yamllint_config = YamlLintConfig(content="extends: default")

    if config_examples:
        yamllint_config_examples = YamlLintConfig(file=config_examples)
    else:
        yamllint_config_examples = yamllint_config

    errors: list[dict[str, t.Any]] = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        if path.endswith(".py"):
            process_python_file(errors, path, yamllint_config, yamllint_config_examples)
        if path.endswith((".yml", ".yaml")):
            process_sidecar_docs_file(errors, path, yamllint_config_examples)

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
