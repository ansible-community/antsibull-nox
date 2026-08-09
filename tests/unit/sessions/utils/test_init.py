# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

from antsibull_nox.sessions.utils import (
    _is_in_ci,
    _is_in_gha,
    compose_description,
    normalize_session_name,
)

from ...utils import set_environ


def test__is_in_gha() -> None:
    with set_environ("GITHUB_ACTION", None):
        assert _is_in_gha() is False
    with set_environ("GITHUB_ACTION", ""):
        assert _is_in_gha() is False
    with set_environ("GITHUB_ACTION", "1"):
        assert _is_in_gha() is True


def test__is_in_ci() -> None:
    with set_environ("CI", None):
        with set_environ("TF_BUILD", None):
            with set_environ("SYSTEM_COLLECTIONURI", None):
                # Not inside CI
                assert _is_in_ci() is False
                with set_environ("CI", "True"):  # must be lower-case
                    assert _is_in_ci() is False
                with set_environ("TF_BUILD", "true"):  # must be capitalized
                    assert _is_in_ci() is False
                with set_environ("SYSTEM_COLLECTIONURI", "foobar"):
                    assert _is_in_ci() is False

                # Inside CI
                with set_environ("CI", "true"):
                    assert _is_in_ci() is True
                with set_environ("TF_BUILD", "True"):
                    assert _is_in_ci() is True
                with set_environ("SYSTEM_COLLECTIONURI", "https://dev.azure.com/"):
                    assert _is_in_ci() is True


def test_compose_description() -> None:
    assert compose_description(programs={}) == ""
    assert compose_description(prefix="foo", programs={}) == "foo"
    assert (
        compose_description(prefix={"one": "foo", "other": "bar"}, programs={}) == "bar"
    )

    programs: dict[str, str | bool | None] = {"p1": True, "p2": None, "p3": False}
    assert compose_description(programs=programs) == "p1"
    assert compose_description(prefix="foo", programs=programs) == "foo p1"
    assert (
        compose_description(prefix={"one": "foo", "other": "bar"}, programs=programs)
        == "foo p1"
    )

    programs = {"p1": True, "p2": None, "p3": False, "p4": "v4"}
    assert compose_description(programs=programs) == "p1 and p4 (v4)"
    assert compose_description(prefix="foo", programs=programs) == "foo p1 and p4 (v4)"
    assert (
        compose_description(prefix={"one": "foo", "other": "bar"}, programs=programs)
        == "bar p1 and p4 (v4)"
    )

    programs = {"p1": True, "p2": None, "p3": "v3", "p4": "v4"}
    assert compose_description(programs=programs) == "p1, p3 (v3), and p4 (v4)"
    assert (
        compose_description(prefix="foo", programs=programs)
        == "foo p1, p3 (v3), and p4 (v4)"
    )
    assert (
        compose_description(prefix={"one": "foo", "other": "bar"}, programs=programs)
        == "bar p1, p3 (v3), and p4 (v4)"
    )


def test_normalize_session_name() -> None:
    assert normalize_session_name("") == ""
    assert normalize_session_name("foo") == "foo"
    assert normalize_session_name("foo-bar") == "foo-bar"
    assert normalize_session_name("foo/bar") == "foo-bar"
