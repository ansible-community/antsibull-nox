# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Python version utilities.
"""

from __future__ import annotations

import functools
import shutil
import subprocess
from pathlib import Path

from .utils import Version

# The following contains Python version candidates
_PYTHON_VERSIONS_TO_TRY: tuple[Version, ...] = tuple(
    Version.parse(v)
    for v in [
        # Python 2:
        "2.6",
        "2.7",
        # Python 3:
        "3.5",
        "3.6",
        "3.7",
        "3.8",
        "3.9",
        "3.10",
        "3.11",
        "3.12",
        "3.13",
        "3.14",
        # "3.15",
        # "3.16",
    ]
)


@functools.cache
def get_installed_python_versions() -> dict[Version, Path]:
    """
    Return a map of supported Python versions for which interpreters exist and are on the path,
    mapped to an executable.
    """
    result = {}

    # Look for pythonX.Y binaries
    for candidate in _PYTHON_VERSIONS_TO_TRY:
        if exe := shutil.which(f"python{candidate}"):
            result[candidate] = Path(exe)

    # Look for python, python2, python3 binaries and determine their version
    for executable in ("python", "python2", "python3"):
        exe = shutil.which(executable)
        if exe:
            script = "import platform; print('.'.join(platform.python_version().split('.')[:2]))"
            exe_result = subprocess.run(
                [exe, "-c", script],
                check=False,
                text=True,
                capture_output=True,
            )
            if exe_result.returncode == 0 and exe_result.stdout:
                try:
                    version = Version.parse(exe_result.stdout.strip())
                except (AttributeError, ValueError):
                    continue
                else:
                    result.setdefault(version, Path(exe))

    return result


__all__ = [
    "get_installed_python_versions",
]
