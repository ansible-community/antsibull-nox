# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox sessions.
"""

from __future__ import annotations

from .collections import (  # Re-export for usage in noxfiles
    CollectionSetup,
    prepare_collections,
)

__all__ = [
    "CollectionSetup",
    "prepare_collections",
]
