# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

# pylint: disable=missing-function-docstring

"""
Helpers for testing.
"""

from __future__ import annotations

import pytest

from antsibull_nox.vcs.factory import get_vcs_provider
from antsibull_nox.vcs.git import GitProvider


def test_get_vcs_provider() -> None:
    with pytest.raises(RuntimeError):
        get_vcs_provider("foo")  # type: ignore[arg-type]

    assert isinstance(get_vcs_provider("git"), GitProvider)
