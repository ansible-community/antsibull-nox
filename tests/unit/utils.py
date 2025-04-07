# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

"""
Helpers for testing.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def chdir(dir: Path):
    current = Path.cwd()
    try:
        os.chdir(dir)
        yield
    finally:
        os.chdir(current)
