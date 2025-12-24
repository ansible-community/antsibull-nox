#!/usr/bin/env python

# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Prevent unwanted files from being added to the source tree."""

from __future__ import annotations

import os
import sys

from antsibull_nox.data.antsibull_nox_data_util import (
    Message,
    get_bool,
    get_list_of_strings,
    report_result,
    setup,
)


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()

    module_extensions = tuple(
        sorted(
            get_list_of_strings(
                extra_data,
                "module_extensions",
                default=[
                    ".cs",
                    ".ps1",
                    ".psm1",
                    ".py",
                ],
            )
        )
    )

    other_extensions = tuple(
        sorted(
            get_list_of_strings(
                extra_data,
                "other_extensions",
                default=[
                    ".py",
                    ".pyi",
                ],
            )
        )
    )

    yaml_extensions = set(
        get_list_of_strings(
            extra_data,
            "yaml_extensions",
            default=[
                ".yml",
                ".yaml",
            ],
        )
    )

    skip_paths = set(get_list_of_strings(extra_data, "skip_paths", default=[]))

    skip_directories = tuple(
        get_list_of_strings(extra_data, "skip_directories", default=[])
    )

    yaml_directories = tuple(
        get_list_of_strings(
            extra_data,
            "yaml_directories",
            default=[
                "plugins/test/",
                "plugins/filter/",
            ],
        )
    )

    allow_symlinks = get_bool(extra_data, "allow_symlinks")

    messages: list[Message] = []
    for path in paths:
        if not path.startswith("plugins/"):
            continue

        if path in skip_paths:
            continue

        if any(path.startswith(skip_directory) for skip_directory in skip_directories):
            continue

        if os.path.islink(path):
            if not allow_symlinks:
                messages.append(
                    Message(
                        file=path,
                        start=None,
                        end=None,
                        level="error",
                        id=None,
                        message="is a symbolic link",
                    )
                )
        elif not os.path.isfile(path):
            messages.append(
                Message(
                    file=path,
                    start=None,
                    end=None,
                    level="error",
                    id=None,
                    message="is not a regular file",
                )
            )

        ext = os.path.splitext(path)[1]

        if ext in yaml_extensions and any(
            path.startswith(yaml_directory) for yaml_directory in yaml_directories
        ):
            continue

        extensions = (
            module_extensions
            if path.startswith("plugins/modules/")
            else other_extensions
        )

        if ext not in extensions:
            messages.append(
                Message(
                    file=path,
                    start=None,
                    end=None,
                    level="error",
                    id=None,
                    message=f"extension must be one of: {', '.join(extensions)}",
                )
            )

    return report_result(messages)


if __name__ == "__main__":
    sys.exit(main())
