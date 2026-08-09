# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

import pytest

from antsibull_nox.sessions.utils.package_versions import is_new_enough


def test_is_new_enough() -> None:
    assert is_new_enough(None, min_version="1.0.0") is True
    assert is_new_enough(None, min_version="1") is True
    assert is_new_enough("2", min_version="1.0.0") is True
    assert is_new_enough("2", min_version="1") is True
    assert is_new_enough("2", min_version="3.0.0") is False
    assert is_new_enough("2", min_version="3") is False
    assert is_new_enough("2.0a1", min_version="2.0") is False
    assert is_new_enough("2.0a1", min_version="2.0a1") is True
    assert is_new_enough("2.0a2", min_version="2.0a1") is True
    assert is_new_enough("2.0", min_version="2.0a1") is True

    with pytest.raises(ValueError, match="^Cannot parse actual version 'asdf': "):
        is_new_enough("asdf", min_version="1")

    with pytest.raises(ValueError, match="^Cannot parse minimum version 'asdf': "):
        is_new_enough("1", min_version="asdf")
