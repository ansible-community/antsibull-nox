#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make sure all plugin and module documentation adheres to yamllint."""

from __future__ import annotations

import os
import sys
import traceback

from antsibull_docutils.rst_code_finder import find_code_blocks
from antsibull_nox_data_util import (  # type: ignore
    Location,
    Message,
    get_bool,
    get_list_of_strings,
    report_result,
    setup,
)


def process_rst_file(
    messages: list[Message],
    path: str,
    *,
    codeblocks_restrict_types: list[str] | None,
    codeblocks_restrict_type_exact_case: bool,
    codeblocks_allow_without_type: bool,
    codeblocks_allow_literal_blocks: bool,
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
                message=f"Error while reading content: {type(exc)}:"
                f" {exc}; traceback: {traceback.format_exc()!r}",
            ),
        )
        return

    def warn_unknown_block(line: int | str, col: int, content: str) -> None:
        if not codeblocks_allow_literal_blocks:
            messages.append(
                Message(
                    file=path,
                    start=Location(line=line, column=col),
                    end=None,
                    level="warning",
                    id=None,
                    message=(
                        "found unknown literal block! Check for double colons '::'."
                        " If that is not the cause, please report this warning."
                        " It might indicate a bug in the checker"
                        " or an unsupported Sphinx directive."
                        f"\nContent: {content!r}"
                    ),
                )
            )

    for code_block in find_code_blocks(
        content,
        path=path,
        root_prefix="docs/docsite/rst",
        warn_unknown_block=warn_unknown_block,
    ):
        location = Location(
            line=code_block.row_offset + 1,
            column=code_block.col_offset + 1,
            exact=code_block.position_exact,
        )
        note: str | None = None
        if not code_block.position_exact:
            note = (
                "The code block could not be exactly located in the source file."
                " The line/column numbers might be off."
            )

        if code_block.language is None:
            if not codeblocks_allow_without_type:
                msg = "Every code block must have a language."
                if codeblocks_restrict_types is not None:
                    langs = ", ".join(sorted(codeblocks_restrict_types))
                    msg = f"{msg} Allowed languages are: {langs}"
                messages.append(
                    Message(
                        file=path,
                        start=location,
                        end=None,
                        level="error",
                        id=None,
                        message=msg,
                        note=note,
                    )
                )
            continue

        if codeblocks_restrict_types is None:
            continue

        language = code_block.language
        if not codeblocks_restrict_type_exact_case:
            language = language.lower()

        if language not in codeblocks_restrict_types:
            langs = ", ".join(sorted(codeblocks_restrict_types))
            msg = (
                f"Code block with disallowed language {code_block.language!r} found."
                f" Allowed languages are: {langs}"
            )
            messages.append(
                Message(
                    file=path,
                    start=location,
                    end=None,
                    level="error",
                    id=None,
                    message=msg,
                    note=note,
                )
            )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()
    codeblocks_restrict_types = get_list_of_strings(
        extra_data, "codeblocks_restrict_types"
    )
    codeblocks_restrict_type_exact_case = get_bool(
        extra_data, "codeblocks_restrict_type_exact_case", default=True
    )
    codeblocks_allow_without_type = get_bool(
        extra_data, "codeblocks_allow_without_type", default=True
    )
    codeblocks_allow_literal_blocks = get_bool(
        extra_data, "codeblocks_allow_literal_blocks", default=True
    )

    if (
        codeblocks_restrict_types is not None
        and not codeblocks_restrict_type_exact_case
    ):
        codeblocks_restrict_types = [
            language.lower() for language in codeblocks_restrict_types
        ]

    messages: list[Message] = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        process_rst_file(
            messages,
            path,
            codeblocks_restrict_types=codeblocks_restrict_types,
            codeblocks_restrict_type_exact_case=codeblocks_restrict_type_exact_case,
            codeblocks_allow_without_type=codeblocks_allow_without_type,
            codeblocks_allow_literal_blocks=codeblocks_allow_literal_blocks,
        )

    return report_result(messages)


if __name__ == "__main__":
    sys.exit(main())
