# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox sessions.
"""

from __future__ import annotations

import json
import os
import sys

import nox

from .collections import (  # Re-export for usage in noxfiles
    CollectionSetup,
    prepare_collections,
)
from .utils import get_registered_sessions


def add_matrix_generator() -> None:
    """
    Add a session that generates matrixes for CI systems.
    """

    def matrix_generator(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        registered_sessions = get_registered_sessions()

        json_output = os.environ.get("ANTSIBULL_NOX_MATRIX_JSON")
        if json_output:
            print(f"Writing JSON output to {json_output}...")
            with open(json_output, "wt", encoding="utf-8") as f:
                f.write(json.dumps(registered_sessions))

        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            print(f"Writing GitHub output to {github_output}...")
            with open(github_output, "at", encoding="utf-8") as f:
                for name, sessions in registered_sessions.items():
                    f.write(f"{name}={json.dumps(sessions)}\n")

        for name, sessions in sorted(registered_sessions.items()):
            print(f"{name} ({len(sessions)}):")
            for session_data in sessions:
                data = session_data.copy()
                session_name = data.pop("name")
                print(f"  {session_name}: {data}")

        sys.stdout.flush()

    matrix_generator.__doc__ = "Generate matrix for CI systems."
    nox.session(
        name="matrix-generator",
        python=False,
        default=False,
    )(matrix_generator)


__all__ = [
    "CollectionSetup",
    "add_matrix_generator",
    "prepare_collections",
]
