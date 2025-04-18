# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""Lint antsibull-nox config."""

from __future__ import annotations

from .config import lint_config_toml


def lint_config() -> list[str]:
    """
    Lint antsibull-nox config file.
    """
    errors = lint_config_toml()
    return sorted(errors)


__all__ = ["lint_config"]
