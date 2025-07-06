#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Avoid characters / regexes in files."""

from __future__ import annotations

import os
import re
import sys

from antsibull_nox.data.antsibull_nox_data_util import setup
from antsibull_nox.sessions.extra_checks import AvoidCharacterGroup


def compile_patterns(
    config: list[AvoidCharacterGroup], errors: list[str]
) -> list[re.Pattern]:
    patterns: list[re.Pattern] = []
    for group in config:
        patterns.append(re.compile(group.regex))
    return patterns


class File:
    def __init__(self, path: str) -> None:
        self.path = path
        self.content: str | None = None

    def get_content(self) -> str:
        if self.content is None:
            with open(self.path, "r", encoding="utf-8") as f:
                self.content = f.read()
        return self.content


def get_position(content: str, position: int) -> tuple[int, int]:
    try:
        prev_newline_index = content.rindex("\n", 0, position + 1)
        return (
            2 + content[0:prev_newline_index].count("\n"),
            position - prev_newline_index,
        )
    except ValueError:
        # No previous newline, i.e. this is in the first line
        return 1, position + 1


def check(
    file: File, group: AvoidCharacterGroup, pattern: re.Pattern, errors: list[str]
) -> None:
    # Check whether the file is included
    if group.match_extensions is not None:
        if not any(
            file.path.endswith(extension) for extension in group.match_extensions
        ):
            return
    if group.match_paths is not None:
        if file.path not in group.match_paths:
            return
    if group.match_directories is not None:
        if not any(
            file.path.startswith(skip_directory)
            for skip_directory in group.match_directories
        ):
            return

    # Check whether the file is excluded
    if any(file.path.endswith(extension) for extension in group.skip_extensions):
        return
    if file.path in group.skip_paths:
        return
    if any(
        file.path.startswith(skip_directory)
        for skip_directory in group.skip_directories
    ):
        return

    content = file.get_content()
    m = pattern.search(content)
    if not m:
        return

    name = group.name if group.name is not None else group.regex
    error = f"found {name}"

    line, col = get_position(content, m.start())

    errors.append(f"{file.path}:{line}:{col}: {error}")


def scan(
    paths: list[str], config: list[AvoidCharacterGroup], errors: list[str]
) -> None:
    patterns = compile_patterns(config, errors)

    for path in paths:
        if not os.path.isfile(path):
            continue

        try:
            file = File(path)
            for index, group in enumerate(config):
                check(file, group, patterns[index], errors)
        except UnicodeDecodeError:
            errors.append(f"{path}: cannot parse file as UTF-8")
        except Exception as e:
            errors.append(f"{path}: unexpected error: {e}")


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()

    if not isinstance(extra_data.get("config"), list):
        raise ValueError("config is not a list")
    if not all(isinstance(cfg, dict) for cfg in extra_data["config"]):
        raise ValueError("config is not a list of dictionaries")
    config = [AvoidCharacterGroup(**cfg) for cfg in extra_data["config"]]

    errors: list[str] = []
    scan(paths, config, errors)

    for error in sorted(errors):
        print(error)
    return len(errors) > 0


if __name__ == "__main__":
    sys.exit(main())
