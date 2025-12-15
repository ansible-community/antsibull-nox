#!/usr/bin/python

# Copyright (c) 2025 Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
This is a test module.
"""

from __future__ import annotations

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
extends_documentation_fragment:
  - antsibull.coverage.ag
"""

EXAMPLES = r"""
---
- name: Test call
  antsibull.coverage.test:
"""

RETURN = r"""
---
msg:
  description:
    - A nice message.
  type: str
  returned: always
"""

import typing as t  # noqa: E402, pylint: disable=wrong-import-position

from ansible.module_utils.basic import (  # noqa: E402, pylint: disable=wrong-import-position
    AnsibleModule,
)


def compute_result() -> dict[str, t.Any]:
    """
    Compute result.
    """
    return {"msg": "Hello!"}


def main() -> None:
    """
    The module's main function.
    """
    module = AnsibleModule(argument_spec={})
    result = compute_result()
    module.exit_json(**result)


if __name__ == "__main__":
    main()
