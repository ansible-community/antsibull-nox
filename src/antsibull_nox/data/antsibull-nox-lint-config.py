#!/usr/bin/env python

# Copyright (c) 2025, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Run antsibull-nox lint-config."""

from __future__ import annotations

import sys

from antsibull_nox.data.antsibull_nox_data_util import (
    report_result,
    setup,
)
from antsibull_nox.lint_config import lint_config_messages


def main() -> int:
    """Main entry point."""
    _, __ = setup()

    messages = lint_config_messages()
    return report_result(messages)


if __name__ == "__main__":
    sys.exit(main())
