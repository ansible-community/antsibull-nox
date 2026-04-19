# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Decorator for installing packages.
"""

from __future__ import annotations

from collections.abc import Callable

import nox
from nox.registry import Func

from .packages import (
    PackageType,
    PackageTypeOrList,
    install,
    normalize_package_type,
)

NoxSessionFunction = Callable[[nox.Session], None]


def _get_packages(
    *,
    session: nox.Session | None,
    packages: PackageTypeOrList | None = None,
    package_callback: (
        Callable[[nox.Session | None], PackageTypeOrList | None] | None
    ) = None,
) -> list[PackageType]:
    session_packages = []
    if packages is not None:
        session_packages.extend(normalize_package_type(packages))
    if package_callback is not None:
        session_packages.extend(normalize_package_type(package_callback(session)))
    return session_packages


def install_packages(
    *,
    packages: PackageTypeOrList | None = None,
    package_callback: (
        Callable[[nox.Session | None], PackageTypeOrList | None] | None
    ) = None,
) -> Callable[[NoxSessionFunction], NoxSessionFunction]:
    """
    Transforms a nox session function to install Python packages before
    calling the original session function.

    This allows reflective access to the list of Python packages to install.
    """
    if (packages is not None) == (package_callback is not None):
        raise ValueError(
            "Implementation error: install_packages decorator needs exactly"
            " one of packages and package_callback parameter provided"
        )

    def wrapper(session_func: NoxSessionFunction) -> NoxSessionFunction:
        """
        The actual decorator.
        """
        if isinstance(session_func, Func):
            raise ValueError(
                "The @install_packages decorator must be applied to a function"
                " before nox's @session decorator. This means that @install_package"
                " must come after @session when both decorators are applied"
                " next to each other."
            )

        def new_session_func(session: nox.Session) -> None:
            session_packages = _get_packages(
                session=session, packages=packages, package_callback=package_callback
            )
            if session_packages:
                install(session, *session_packages)
            session_func(session)

        new_session_func.__doc__ = session_func.__doc__
        new_session_func.install_packages__packages = packages  # type: ignore
        new_session_func.install_packages__package_callback = package_callback  # type: ignore
        return new_session_func

    return wrapper


def get_session_packages(session: Func) -> list[PackageType] | None:
    """
    Given a nox session function, return a list of packages if applicable.

    If the install_packages decorator was not used, returns ``None`` instead.
    """
    sentinel = object()
    packages = getattr(session.func, "install_packages__packages", sentinel)
    package_callback = getattr(
        session.func, "install_packages__package_callback", sentinel
    )
    if packages is sentinel or package_callback is sentinel:
        return None
    return _get_packages(
        session=None, packages=packages, package_callback=package_callback  # type: ignore
    )


__all__ = [
    "get_session_packages",
    "install_packages",
]
