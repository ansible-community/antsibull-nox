# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

from unittest.mock import MagicMock, patch

from antsibull_nox.sessions.utils.packages import (
    PackageConstraints,
    PackageEditable,
    PackageName,
    PackageRequirements,
    _get_install_params,
    check_package_types,
    normalize_package_type,
)


def test_PackageName() -> None:
    assert list(PackageName("foo").get_pip_install_args()) == ["foo"]


def test_PackageEditable() -> None:
    with patch("antsibull_nox.sessions.utils.packages.ALLOW_EDITABLE", True):
        assert list(PackageEditable("foo").get_pip_install_args()) == ["-e", "foo"]
    with patch("antsibull_nox.sessions.utils.packages.ALLOW_EDITABLE", False):
        assert list(PackageEditable("foo").get_pip_install_args()) == ["foo"]


def test_PackageRequirements() -> None:
    assert list(PackageRequirements("foo").get_pip_install_args()) == ["-r", "foo"]


def test_PackageConstraints() -> None:
    assert list(PackageConstraints("foo").get_pip_install_args()) == ["-c", "foo"]


def test_normalize_package_type() -> None:
    assert normalize_package_type(None) == []
    assert normalize_package_type("foo") == ["foo"]
    assert normalize_package_type(("foo", "bar")) == ["foo", "bar"]
    assert normalize_package_type(PackageName("foo")) == [PackageName("foo")]


def test__get_install_params() -> None:
    assert _get_install_params([]) == []
    assert _get_install_params(["foo"]) == ["foo"]
    assert _get_install_params([PackageName("foo")]) == ["foo"]
    assert _get_install_params([PackageRequirements("foo")]) == ["-r", "foo"]


def test_check_package_types() -> None:
    session = MagicMock()
    check_package_types(session, "foo", [])
    session.warn.assert_not_called()

    session = MagicMock()
    check_package_types(session, "foo", [PackageName("bar")])
    session.warn.assert_not_called()

    session = MagicMock()
    check_package_types(session, "foo", [PackageRequirements("-bar")])
    session.warn.assert_not_called()

    session = MagicMock()
    check_package_types(session, "foo", [PackageName("-bar")])
    session.warn.assert_called_once()
    session.warn.assert_called_once_with(
        "DEPRECATION WARNING: foo contains a package name '-bar' starting with a dash."
        " This behavior is deprecated and will stop working in a future release."
    )

    session = MagicMock()
    check_package_types(session, "foo", [PackageEditable("-bar")])
    session.warn.assert_called_once()
