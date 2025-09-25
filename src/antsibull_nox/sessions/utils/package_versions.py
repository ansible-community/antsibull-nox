# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utils for dealing with packages.
"""

from __future__ import annotations

import json

import nox
from packaging.version import InvalidVersion
from packaging.version import parse as parse_version

from .scripts import run_bare_script


def get_package_versions(
    session: nox.Session,
    /,
    packages: list[str] | str,
    *,
    use_session_python: bool = True,
) -> None | dict[str, str | None]:
    """
    Retrieve the versions of one or more Python packages.
    """
    name = "get-package-versions"
    if isinstance(packages, str):
        packages = [packages]
    if not packages:
        return {}
    result = run_bare_script(
        session,
        name,
        use_session_python=use_session_python,
        files=[],
        extra_data={"packages": packages},
        silent=True,
    )
    if result is None:
        return None
    return json.loads(result)


def get_package_version(
    session: nox.Session,
    /,
    package: str,
    *,
    use_session_python: bool = True,
) -> str | None:
    """
    Retrieve a Python package's version.
    """
    result = get_package_versions(
        session, package, use_session_python=use_session_python
    )
    return None if result is None else result.get(package)


def is_new_enough(actual_version: str | None, *, min_version: str) -> bool:
    """
    Given a program version, compares it to the min_version.
    If the program version is not given, it is assumed to be "new enough".
    """
    if actual_version is None:
        return True
    try:
        act_v = parse_version(actual_version)
    except InvalidVersion as exc:
        raise ValueError(
            f"Cannot parse actual version {actual_version!r}: {exc}"
        ) from exc
    try:
        min_v = parse_version(min_version)
    except InvalidVersion as exc:
        raise ValueError(
            f"Cannot parse minimum version {min_version!r}: {exc}"
        ) from exc
    return act_v >= min_v


__all__ = [
    "get_package_version",
    "get_package_versions",
    "is_new_enough",
]
