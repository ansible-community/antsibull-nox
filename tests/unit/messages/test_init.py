# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

from antsibull_nox.messages import Level, Location, Message


def test_Location() -> None:
    assert Location(line=5) < Location(line=5, column=1)
    assert Location(line=5) <= Location(line=5, column=1)
    assert not (Location(line=5) > Location(line=5, column=1))
    assert not (Location(line=5) >= Location(line=5, column=1))

    assert Location(line=5, column=2) > Location(line=5, column=1, exact=False)
    assert Location(line=5, column=2) >= Location(line=5, column=1, exact=False)
    assert not (Location(line=5, column=2) < Location(line=5, column=1, exact=False))
    assert not (Location(line=5, column=2) <= Location(line=5, column=1, exact=False))

    assert Location(line=5, column=1) > Location(line=5, column=1, exact=False)
    assert Location(line=5, column=1) >= Location(line=5, column=1, exact=False)
    assert not (Location(line=5, column=1) < Location(line=5, column=1, exact=False))
    assert not (Location(line=5, column=1) <= Location(line=5, column=1, exact=False))


def test_Message() -> None:
    a = Message(
        file=None,
        position=None,
        end_position=None,
        level=Level.ERROR,
        id=None,
        message="foo",
    )
    b = Message(
        file=None,
        position=None,
        end_position=None,
        level=Level.ERROR,
        id=None,
        message="bar",
    )
    assert b < a
    assert b <= a
    assert b != a
    assert a > b
    assert a >= b
    assert a != b
