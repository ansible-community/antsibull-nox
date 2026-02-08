# Author: Daniel Brennand <contact@danielbrennand.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Constants for antsibull-nox sessions.
"""

import os

# Taken from:
# https://github.com/ansible/ansible-compat/blob/main/src/ansible_compat/constants.py#L6
# pylint: disable=unsupported-assignment-operation
_ANSIBLE_COMPAT_REQUIREMENTS_FILES = list[str | os.PathLike] = [
    "requirements.yml",
    "roles/requirements.yml",
    "collections/requirements.yml",
    "tests/requirements.yml",
    "tests/integration/requirements.yml",
    "tests/unit/requirements.yml",
]
