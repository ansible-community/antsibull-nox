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

from antsibull_nox_data_util import (  # type: ignore
    Level,
    Location,
    Message,
    report_result,
    setup,
)
from yamllint import linter
from yamllint.cli import find_project_config_filepath
from yamllint.config import YamlLintConfig
from yamllint.linter import PROBLEM_LEVELS

REPORT_LEVELS: dict[PROBLEM_LEVELS, Level] = {
    "warning": "warning",
    "error": "error",
}


def lint(
    *,
    messages: list[Message],
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
            level = REPORT_LEVELS.get(problem.level)
            if level is None:
                continue
            msg = f"{problem.level}: {problem.desc}"
            messages.append(
                Message(
                    file=path,
                    start=Location(line=problem.line, column=problem.column),
                    end=None,
                    level=level,
                    id=problem.rule or None,
                    message=msg,
                )
            )
    except Exception as exc:
        error = str(exc).replace("\n", " / ")
        messages.append(
            Message(
                file=path,
                start=None,
                end=None,
                level="error",
                id=None,
                message=f"Internal error while linting YAML: exception {type(exc)}:"
                f" {error}; traceback: {traceback.format_exc()!r}",
            )
        )


def process_yaml_file(
    messages: list[Message],
    path: str,
    config: YamlLintConfig,
) -> None:
    try:
        with open(path, "rt", encoding="utf-8") as stream:
            data = stream.read()
    except Exception as exc:
        messages.append(
            Message(
                file=path,
                start=None,
                end=None,
                level="error",
                id=None,
                message=f"Error while parsing Python code: exception {type(exc)}:"
                f" {exc}; traceback: {traceback.format_exc()!r}",
            )
        )
        return

    lint(
        messages=messages,
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

    messages: list[Message] = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        process_yaml_file(messages, path, yamllint_config)

    return report_result(messages)


if __name__ == "__main__":
    sys.exit(main())
