# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utils for handling Ansible values.
"""

from __future__ import annotations

import dataclasses
import os
import typing as t


@dataclasses.dataclass
class AnsibleValueExplicit:
    """
    An explicit value.
    """

    value: t.Any

    template_value: str | None = None

    def get_value(self) -> tuple[t.Any, bool]:
        """
        Get the current value, together with a boolean whether this value should be set.
        """
        return self.value, True


@dataclasses.dataclass
class AnsibleValueFromEnv:
    """
    A value taken from an environment variable
    """

    name: str
    fallback: t.Any = None
    unset_if_not_set: bool = False

    template_value: str | None = None

    def get_value(self) -> tuple[t.Any, bool]:
        """
        Get the current value, together with a boolean whether this value should be set.
        """
        if self.name in os.environ:
            return os.environ[self.name], True
        if self.unset_if_not_set:
            return None, False
        return self.fallback, True


AnsibleValue = t.Union[
    AnsibleValueExplicit,
    AnsibleValueFromEnv,
]


__all__ = [
    "AnsibleValueExplicit",
    "AnsibleValueFromEnv",
    "AnsibleValue",
]
