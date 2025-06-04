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
    get_list_of_strings,
    setup,
)


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()

    skip_paths = set(get_list_of_strings(extra_data, "skip_paths", default=[]))

    skip_directories = tuple(
        get_list_of_strings(extra_data, "skip_directories", default=[])
    )

    errors: list[str] = []
    for path in paths:
        if path in skip_paths:
            continue

        if any(path.startswith(skip_directory) for skip_directory in skip_directories):
            continue

        if not os.path.isfile(path):
            continue

        with open(path, "r", encoding="latin1") as f:
            for i, line in enumerate(f):
                line = line.rstrip("\n\r")
                if line.rstrip() != line:
                    errors.append(f"{path}:{i + 1}: found trailing whitespace")

    for error in sorted(errors):
        print(error)
    return len(errors) > 0


if __name__ == "__main__":
    sys.exit(main())
