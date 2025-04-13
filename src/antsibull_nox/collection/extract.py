# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Extract tarballs.
"""

from __future__ import annotations

import tarfile
from pathlib import Path


def extract_tarball(*, tarball: Path, destination: Path) -> None:
    """
    Extract the contents of the tarball ``tarball`` to the destination directory ``destination``.
    """
    destination.mkdir(exist_ok=True, parents=True)
    with tarfile.open(tarball) as tar:
        tar.extractall(path=destination, filter="data")
