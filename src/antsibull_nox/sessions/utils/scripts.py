# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utils for handling scripts.
"""

from __future__ import annotations

import sys
import typing as t
from pathlib import Path

import nox

from ...data_util import prepare_data_script
from ...paths import (
    find_data_directory,
    list_all_files,
)
from .paths import filter_files_cd


def run_bare_script(
    session: nox.Session,
    /,
    name: str,
    *,
    use_session_python: bool = False,
    files: list[Path] | None = None,
    extra_data: dict[str, t.Any] | None = None,
    silent: bool = False,
    with_cd: bool = False,
) -> str | None:
    """
    Run a bare script included in antsibull-nox's data directory.
    """
    if files is None:
        files = list_all_files()
    if with_cd:
        files = filter_files_cd(files)
        if not files:
            session.warn(f"Skipping {name} (no files to process)")
            return None
    data = prepare_data_script(
        session,
        base_name=name,
        paths=files,
        extra_data=extra_data,
    )
    python = sys.executable
    env = {}
    if use_session_python:
        python = "python"
        env["PYTHONPATH"] = str(find_data_directory())
    return session.run(
        python,
        find_data_directory() / f"{name}.py",
        "--data",
        data,
        external=True,
        silent=silent,
        env=env,
    )


__all__ = [
    "run_bare_script",
]
