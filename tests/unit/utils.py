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
import typing as t
from pathlib import Path


@contextlib.contextmanager
def chdir(dir: Path):
    current = Path.cwd()
    try:
        os.chdir(dir)
        yield
    finally:
        os.chdir(current)


def set_environ_value(env_var: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(env_var, None)
    else:
        os.environ[env_var] = value


@contextlib.contextmanager
def set_environ(env_var: str, value: str | None) -> t.Iterator[None]:
    old_value = os.environ.get(env_var)
    try:
        set_environ_value(env_var, value)
        yield
    finally:
        set_environ_value(env_var, old_value)
