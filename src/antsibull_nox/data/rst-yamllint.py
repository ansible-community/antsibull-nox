#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make sure all YAML in RST extra documentation adheres to yamllint."""

from __future__ import annotations

import io
import os
import sys
import traceback

from antsibull_docutils.rst_code_finder import (
    find_code_blocks,
    mark_antsibull_code_block,
)
from antsibull_nox_data_util import (  # type: ignore
    Level,
    Location,
    Message,
    report_result,
    setup,
)
from docutils import nodes
from docutils.parsers.rst import Directive
from yamllint import linter
from yamllint.config import YamlLintConfig
from yamllint.linter import PROBLEM_LEVELS

REPORT_LEVELS: dict[PROBLEM_LEVELS, Level] = {
    "warning": "warning",
    "error": "error",
}

YAML_LANGUAGES = {"yaml", "yaml+jinja"}


def lint(
    *,
    messages: list[Message],
    path: str,
    data: str,
    row_offset: int,
    col_offset: int,
    config: YamlLintConfig,
    note: str | None = None,
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
            level = REPORT_LEVELS.get(problem.level)
            if level is None:
                continue
            msg = f"{problem.level}: {problem.desc}"
            if problem.rule:
                msg += f"  ({problem.rule})"
            messages.append(
                Message(
                    file=path,
                    start=Location(
                        line=row_offset + problem.line,
                        # The col_offset is only valid for line 1; otherwise the offset is 0
                        column=(col_offset if problem.line == 1 else 0)
                        + problem.column,
                    ),
                    end=None,
                    level=level,
                    id=None,
                    message=msg,
                    note=note,
                )
            )
    except Exception as exc:
        error = str(exc).replace("\n", " / ")
        messages.append(
            Message(
                file=path,
                start=Location(line=row_offset + 1, column=col_offset + 1),
                end=None,
                level="error",
                id=None,
                message=(
                    f"Internal error while linting YAML: exception {type(exc)}:"
                    f" {error}; traceback: {traceback.format_exc()!r}"
                ),
                note=note,
            )
        )


_ANSIBLE_OUTPUT_DATA_LANGUAGE = "ansible-output-data-FPho6oogookao7okinoX"
_ANSIBLE_OUTPUT_META_LANGUAGE = "ansible-output-meta-FPho6oogookao7okinoX"


class AnsibleOutputDataDirective(Directive):
    has_content = True

    def run(self) -> list[nodes.literal_block]:
        code = "\n".join(self.content)
        literal = nodes.literal_block(code, code)
        literal["classes"].append("code-block")
        mark_antsibull_code_block(
            literal,
            language=_ANSIBLE_OUTPUT_DATA_LANGUAGE,
            content_offset=self.content_offset,
        )
        return [literal]


class AnsibleOutputMetaDirective(Directive):
    has_content = True

    def run(self) -> list[nodes.literal_block]:
        code = "\n".join(self.content)
        literal = nodes.literal_block(code, code)
        literal["classes"].append("code-block")
        mark_antsibull_code_block(
            literal,
            language=_ANSIBLE_OUTPUT_META_LANGUAGE,
            content_offset=self.content_offset,
        )
        return [literal]


def process_rst_file(
    messages: list[Message],
    path: str,
    config: YamlLintConfig,
) -> None:
    try:
        with open(path, "rt", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        messages.append(
            Message(
                file=path,
                start=None,
                end=None,
                level="error",
                id=None,
                message=(
                    f"Error while reading content: {type(exc)}:"
                    f" {exc}; traceback: {traceback.format_exc()!r}"
                ),
            )
        )
        return

    def warn_unknown_block(line: int | str, col: int, content: str) -> None:
        messages.append(
            Message(
                file=path,
                start=Location(line=line, column=col),
                end=None,
                level="error",
                id=None,
                message=(
                    "Warning: found unknown literal block! Check for double colons '::'."
                    " If that is not the cause, please report this warning."
                    " It might indicate a bug in the checker or an unsupported Sphinx directive."
                    f" Content: {content!r}"
                ),
            )
        )

    for code_block in find_code_blocks(
        content,
        path=path,
        root_prefix="docs/docsite/rst",
        warn_unknown_block=warn_unknown_block,
        extra_directives={
            "ansible-output-data": AnsibleOutputDataDirective,
            "ansible-output-meta": AnsibleOutputMetaDirective,
        },
    ):
        if (
            code_block.language or ""
        ).lower() not in YAML_LANGUAGES and code_block.language not in (
            _ANSIBLE_OUTPUT_DATA_LANGUAGE,
            _ANSIBLE_OUTPUT_META_LANGUAGE,
        ):
            continue

        note: str | None = None
        if not code_block.position_exact:
            note = (
                "The code block could not be exactly located in the source file."
                " The line/column numbers might be off."
            )

        # Parse the (remaining) string content
        lint(
            messages=messages,
            path=path,
            data=code_block.content,
            row_offset=code_block.row_offset,
            col_offset=code_block.col_offset,
            config=config,
            note=note,
        )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()
    config: str | None = extra_data.get("config")

    if config:
        yamllint_config = YamlLintConfig(file=config)
    else:
        yamllint_config = YamlLintConfig(content="extends: default")

    messages: list[Message] = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        process_rst_file(messages, path, yamllint_config)

    return report_result(messages)


if __name__ == "__main__":
    sys.exit(main())
