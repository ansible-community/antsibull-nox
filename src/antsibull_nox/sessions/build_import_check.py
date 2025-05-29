# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox build import check session.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import nox

from ..collection import (
    build_collection,
)
from .utils import (
    ci_group,
    compose_description,
    install,
    nox_has_verbosity,
    silence_run_verbosity,
)


def add_build_import_check(
    *,
    make_build_import_check_default: bool = True,
    ansible_core_package: str = "ansible-core",
    run_galaxy_importer: bool = True,
    galaxy_importer_package: str = "galaxy-importer",
    galaxy_importer_config_path: (
        str | os.PathLike | None
    ) = None,  # https://github.com/ansible/galaxy-importer#configuration
    galaxy_importer_always_show_logs: bool = False,
) -> None:
    """
    Add license-check session for license checks.
    """

    def compose_dependencies() -> list[str]:
        deps = [ansible_core_package]
        if run_galaxy_importer:
            deps.append(galaxy_importer_package)
        return deps

    def build_import_check(session: nox.Session) -> None:
        install(session, *compose_dependencies())

        tarball, _, __ = build_collection(session)

        if run_galaxy_importer and tarball:
            env = {}
            if galaxy_importer_config_path:
                env["GALAXY_IMPORTER_CONFIG"] = str(
                    Path(galaxy_importer_config_path).absolute()
                )
            assert tarball.parent is not None
            with session.chdir(tarball.parent), silence_run_verbosity():
                import_log = session.run(
                    "python",
                    "-m",
                    "galaxy_importer.main",
                    tarball.name,
                    env=env,
                    silent=True,
                )
            if import_log is not None:
                with ci_group("Run Galaxy importer") as (indent, is_collapsed):
                    if (
                        is_collapsed
                        or galaxy_importer_always_show_logs
                        or nox_has_verbosity()
                    ):
                        for line in import_log.splitlines():
                            print(f"{indent}{line}")
                        sys.stdout.flush()
                error_prefix = "ERROR:"
                errors = []
                for line in import_log.splitlines():
                    if line.startswith(error_prefix):
                        errors.append(line[len(error_prefix) :].strip())
                if errors:
                    messages = "\n".join(f"* {error}" for error in errors)
                    session.warn(
                        "Galaxy importer emitted the following non-fatal"
                        f" error{'' if len(errors) == 1 else 's'}:\n{messages}"
                    )

    build_import_check.__doc__ = compose_description(
        prefix={
            "one": "Run build and import checker:",
            "other": "Run build and import checkers:",
        },
        programs={
            "build-collection": True,
            "galaxy-importer": (
                "test whether Galaxy will import built collection"
                if run_galaxy_importer
                else False
            ),
        },
    )
    nox.session(
        name="build-import-check",
        default=make_build_import_check_default,
    )(build_import_check)


__all__ = [
    "add_build_import_check",
]
