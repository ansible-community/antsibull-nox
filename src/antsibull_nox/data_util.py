# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utility code for scripts in data.
"""

from __future__ import annotations

import json
import typing as t
from pathlib import Path

import nox


def prepare_data_script(
    session: nox.Session,
    *,
    base_name: str,
    paths: list[Path],
    extra_data: dict[str, t.Any] | None = None,
) -> Path:
    """
    Prepare a data JSON file for the extra sanity check scripts.
    """
    cwd = Path.cwd()
    data = {}
    data["paths"] = [str(path.relative_to(cwd)) for path in paths]
    if extra_data:
        data.update(extra_data)
    file = Path(session.create_tmp()) / f"{base_name}-data.json"
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return file
