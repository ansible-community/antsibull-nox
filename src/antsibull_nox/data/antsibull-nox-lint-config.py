#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Run antsibull-nox lint-config."""

from __future__ import annotations

import sys

from antsibull_nox.data.antsibull_nox_data_util import setup
from antsibull_nox.lint_config import lint_config


def main() -> int:
    """Main entry point."""
    _, __ = setup()

    errors = lint_config()
    for error in errors:
        print(error)
    return len(errors) > 0


if __name__ == "__main__":
    sys.exit(main())
