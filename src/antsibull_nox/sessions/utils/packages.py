# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Utils for dealing with packages.
"""

from __future__ import annotations

import dataclasses
import os
import typing as t
from collections.abc import Iterator, Sequence

import nox

from . import IN_CI as _IN_CI

ALLOW_EDITABLE = os.environ.get("ALLOW_EDITABLE", str(not _IN_CI)).lower() in (
    "1",
    "true",
)


@dataclasses.dataclass
class PackageName:
    """
    A PyPI package name.
    """

    name: str

    def get_pip_install_args(self) -> Iterator[str]:
        """
        Yield arguments to 'pip install'.
        """
        yield self.name


@dataclasses.dataclass
class PackageEditable:
    """
    A PyPI package name that should be installed editably (if allowed).
    """

    name: str

    def get_pip_install_args(self) -> Iterator[str]:
        """
        Yield arguments to 'pip install'.
        """
        # Don't install in editable mode in CI or if it's explicitly disabled.
        # This ensures that the wheel contains all of the correct files.
        if ALLOW_EDITABLE:
            yield "-e"
        yield self.name


@dataclasses.dataclass
class PackageRequirements:
    """
    A Python requirements.txt file.
    """

    file: str

    def get_pip_install_args(self) -> Iterator[str]:
        """
        Yield arguments to 'pip install'.
        """
        yield "-r"
        yield self.file


@dataclasses.dataclass
class PackageConstraints:
    """
    A Python constraints.txt file.
    """

    file: str

    def get_pip_install_args(self) -> Iterator[str]:
        """
        Yield arguments to 'pip install'.
        """
        yield "-c"
        yield self.file


PackageType = t.Union[
    str,
    PackageName,
    PackageEditable,
    PackageRequirements,
    PackageConstraints,
]

PackageTypeOrList = t.Union[PackageType, Sequence[PackageType]]


def normalize_package_type(packages: PackageTypeOrList | None) -> list[PackageType]:
    """
    Given a package type or a list of package types or ``None``,
    convert this to a list of package types.
    """
    if packages is None:
        return []
    # A str is a Sequence as well.
    if isinstance(packages, Sequence) and not isinstance(packages, str):
        return list(packages)  # return a copy
    return [packages]


def _get_install_params(packages: Sequence[PackageType]) -> list[str]:
    new_args: list[str] = []
    for arg in packages:
        if isinstance(arg, str):
            new_args.append(arg)
        else:
            new_args.extend(arg.get_pip_install_args())
    return new_args


def install(session: nox.Session, *args: PackageType, **kwargs):
    """
    Install Python packages.
    """
    if not args:
        return

    # nox --no-venv
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn(f"No venv. Skipping installation of {args}")
        return

    new_args = _get_install_params(args)
    session.install(*new_args, "-U", **kwargs)


def check_package_types(
    session: nox.Session, arg_name: str, packages: list[PackageType]
) -> list[PackageType]:
    """
    Given a list of packages, check for invalid package names.
    """
    for package in packages:
        if not isinstance(package, (PackageName, PackageEditable)):
            continue
        if package.name.startswith("-"):
            session.warn(
                f"DEPRECATION WARNING: {arg_name} contains a package name"
                f" {package.name!r} starting with a dash."
                " This behavior is deprecated and will stop working in a future release."
            )
    return packages


__all__ = [
    "PackageName",
    "PackageEditable",
    "PackageRequirements",
    "PackageType",
    "check_package_types",
    "install",
    "normalize_package_type",
]
