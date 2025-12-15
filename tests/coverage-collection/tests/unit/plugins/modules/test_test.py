# Copyright (c) 2025 Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Some basic unit tests.
"""

from __future__ import annotations

from ansible_collections.antsibull.coverage.plugins.modules.test import compute_result


def test_compute_result() -> None:
    """
    Test compute_result().
    """
    result = compute_result()
    assert result == {"msg": "Hello!"}
