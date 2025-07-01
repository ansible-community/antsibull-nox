# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Antsibull Nox Helper.
"""

from __future__ import annotations

from .config import (
    CONFIG_FILENAME,
    load_config_from_toml,
)
from .interpret_config import interpret_config
from .sessions.ansible_test import add_ansible_test_session

__version__ = "0.7.0"


def load_antsibull_nox_toml() -> None:
    """
    Load and interpret antsibull-nox.toml config file.
    """
    config = load_config_from_toml(CONFIG_FILENAME)
    interpret_config(config)


# pylint:disable=duplicate-code
__all__ = (
    "__version__",
    "add_ansible_test_session",
    "load_antsibull_nox_toml",
)
