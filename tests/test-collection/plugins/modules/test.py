#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
This is a test module.
"""


DOCUMENTATION = r"""
---
module: test
short_description: Test module
author:
  - Felix Fontein (@felixfontein)
description:
  - Does nothing.
notes:
  - Does not support C(check_mode).
"""

from ansible.module_utils.basic import (  # noqa: E402, pylint: disable=wrong-import-position
    AnsibleModule,
)


def main():
    """
    The module's main function.
    """
    module = AnsibleModule(argument_spec={})
    module.exit_json(msg="Hello!")


if __name__ == "__main__":
    main()
