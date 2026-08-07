# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

from antsibull_nox._pydantic import (
    _parse_pydantic_version,
)


def test__parse_pydantic_version() -> None:
    pydantic_version = _parse_pydantic_version()
    assert len(pydantic_version) == 2
    assert pydantic_version >= (2, 0)
    assert pydantic_version < (3, 0)
