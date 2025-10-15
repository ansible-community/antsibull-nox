# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Antsibull Nox Helper.
"""

from __future__ import annotations

from pathlib import Path

from .cd import init_cd
from .config import (
    CONFIG_FILENAME,
    load_config_from_toml,
)
from .interpret_config import interpret_config
from .sessions.ansible_test import add_ansible_test_session

__version__ = "1.3.2"


def load_antsibull_nox_toml() -> None:
    """
    Load and interpret antsibull-nox.toml config file.
    """
    config_path = Path(CONFIG_FILENAME)
    config = load_config_from_toml(config_path)
    init_cd(config=config, config_path=config_path, ignore_previous_calls=True)
    interpret_config(config)


# pylint:disable=duplicate-code
__all__ = (
    "__version__",
    "add_ansible_test_session",
    "load_antsibull_nox_toml",
)
