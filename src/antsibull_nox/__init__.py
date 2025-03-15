# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Antsibull Nox Helper.
"""

from __future__ import annotations

from .sessions import add_lint_sessions  # noqa: F401

__version__ = "0.0.1"

__all__ = ("__version__",)
