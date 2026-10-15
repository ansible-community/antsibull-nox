# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Collection releasers base classes.
"""

from __future__ import annotations

import abc


class BaseReleaser(metaclass=abc.ABCMeta):
    """
    Base releaser class.
    """


__all__ = ("BaseReleaser",)
