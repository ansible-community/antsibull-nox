#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Retrieve the version of one or more packages."""

from __future__ import annotations

import json
import sys
from importlib.metadata import PackageNotFoundError, version

from antsibull_nox_data_util import get_list_of_strings, setup  # type: ignore


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()

    packages = get_list_of_strings(extra_data, "packages", default=[])

    result: dict[str, str | None] = {}
    for package in packages:
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
