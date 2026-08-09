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

from antsibull_nox.vcs.utils import SortableBranchName, matches


def test_SortableBranchName() -> None:
    assert str(SortableBranchName("")) == ""
    assert str(SortableBranchName("foo")) == "foo"
    assert str(SortableBranchName("stable-2.9")) == "stable-2.9"
    assert str(SortableBranchName("stable-2.09")) == "stable-2.09"
    assert str(SortableBranchName("stable-2.10")) == "stable-2.10"

    assert repr(SortableBranchName("")) == "SortableBranchName('', parts=)"
    assert (
        repr(SortableBranchName("foo"))
        == "SortableBranchName('foo', parts='f','o','o')"
    )
    assert (
        repr(SortableBranchName("stable-2.9"))
        == "SortableBranchName('stable-2.9', parts='s','t','a','b','l','e','-','2','.','9')"
    )
    assert (
        repr(SortableBranchName("stable-2.09"))
        == "SortableBranchName('stable-2.09', parts='s','t','a','b','l','e','-','2','.','09')"
    )
    assert (
        repr(SortableBranchName("stable-2.10"))
        == "SortableBranchName('stable-2.10', parts='s','t','a','b','l','e','-','2','.','10')"
    )

    assert not (SortableBranchName("stable-2.9") == 42)
    assert SortableBranchName("stable-2.09") < SortableBranchName("stable-2.10")
    assert SortableBranchName("stable-2.09") < SortableBranchName("stable-2.9")
    assert not (SortableBranchName("stable-2.10") < SortableBranchName("stable-2.09"))
    assert not (SortableBranchName("stable-2.9") < SortableBranchName("stable-2.09"))
    assert SortableBranchName("stable-2.9") < SortableBranchName("stable-2.10")
    assert not (SortableBranchName("stable-2.9") > SortableBranchName("stable-2.10"))
    assert SortableBranchName("stable-2.9") <= SortableBranchName("stable-2.10")
    assert not (SortableBranchName("stable-2.9") >= SortableBranchName("stable-2.10"))
    assert SortableBranchName("stable-2.9") != SortableBranchName("stable-2.10")
    assert SortableBranchName("stable-2.9") == SortableBranchName("stable-2.9")
    assert SortableBranchName("stable-2.9") <= SortableBranchName("stable-2.9")
    assert SortableBranchName("stable-2.9") >= SortableBranchName("stable-2.9")
    assert not (SortableBranchName("stable-2.9") != SortableBranchName("stable-2.9"))
    assert not (SortableBranchName("stable-2.9") < SortableBranchName("stable-2.9"))
    assert not (SortableBranchName("stable-2.9") > SortableBranchName("stable-2.9"))
    assert SortableBranchName("stable-2") < SortableBranchName("stable-2.10")
    assert SortableBranchName("stable-2") <= SortableBranchName("stable-2.10")
    assert SortableBranchName("stable-3") > SortableBranchName("stable-2.10")
    assert SortableBranchName("stable-3") >= SortableBranchName("stable-2.10")
    assert SortableBranchName(" ") < SortableBranchName("1")
    assert not (SortableBranchName("a") < SortableBranchName("1"))
    assert SortableBranchName("1") < SortableBranchName("a")
    assert not (SortableBranchName("1") < SortableBranchName(" "))


def test_matches() -> None:
    assert not matches("", [])
    assert matches("stable-5", ["stable-*"])
    assert matches("stable-", ["stable-*"])
    assert not matches("stable", ["stable-*"])
