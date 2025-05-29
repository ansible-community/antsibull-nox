# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Handle Ansible collections.
"""

from __future__ import annotations

from .build import build_collection
from .data import CollectionData, CollectionSource, SetupResult
from .install import (
    Runner,
    setup_collection_sources,
    setup_collections,
    setup_current_tree,
)
from .search import CollectionList, load_collection_data_from_disk
from .utils import force_collection_version

__all__ = [
    "CollectionData",
    "CollectionList",
    "CollectionSource",
    "SetupResult",
    "Runner",
    "build_collection",
    "force_collection_version",
    "load_collection_data_from_disk",
    "setup_collections",
    "setup_current_tree",
    "setup_collection_sources",
]
