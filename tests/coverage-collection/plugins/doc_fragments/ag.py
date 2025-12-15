# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see COPYING
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Foo documentation fragment.
"""

from __future__ import annotations


class ModuleDocFragment:  # pylint: disable=too-few-public-methods
    """
    Standard documentation fragment
    """

    DOCUMENTATION = r"""
---
options: {}
attributes:
  action_group:
    description: >-
      Use C(group/antsibull.coverage.foo) in C(module_defaults)
      to set defaults for this module.
    support: full
    membership:
      - antsibull.coverage.foo
"""
