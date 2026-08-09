# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

from antsibull_nox.sessions.utils.values import (
    AnsibleValueExplicit,
    AnsibleValueFromEnv,
)

from ...utils import set_environ


def test_AnsibleValueExplicit() -> None:
    v = AnsibleValueExplicit("foo")
    assert v.get_value() == ("foo", True)


def test_AnsibleValueFromEnv() -> None:
    v = AnsibleValueFromEnv("foo")
    with set_environ("foo", "bar"):
        assert v.get_value() == ("bar", True)
    with set_environ("foo", None):
        assert v.get_value() == (None, True)

    v = AnsibleValueFromEnv("foo", fallback="baz")
    with set_environ("foo", None):
        assert v.get_value() == ("baz", True)

    v = AnsibleValueFromEnv("foo", fallback="baz", unset_if_not_set=True)
    with set_environ("foo", None):
        assert v.get_value() == (None, False)
