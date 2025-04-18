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
from pathlib import Path

import nox

from ..collection import (
    force_collection_version,
    load_collection_data_from_disk,
)
from ..paths import (
    copy_collection,
    remove_path,
)
from . import (
    _ci_group,
    _compose_description,
    install,
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

        tmp = Path(session.create_tmp())
        collection_dir = tmp / "collection"
        remove_path(collection_dir)
        copy_collection(Path.cwd(), collection_dir)

        collection = load_collection_data_from_disk(
            collection_dir, accept_manifest=False
        )
        version = collection.version
        if not version:
            version = "0.0.1"
            force_collection_version(collection_dir, version=version)

        with session.chdir(collection_dir):
            build_ran = session.run("ansible-galaxy", "collection", "build") is not None

        tarball = (
            collection_dir
            / f"{collection.namespace}-{collection.name}-{version}.tar.gz"
        )
        if build_ran and not tarball.is_file():
            files = "\n".join(
                f"* {path.name}"
                for path in collection_dir.iterdir()
                if not path.is_dir()
            )
            session.error(f"Cannot find file {tarball}! List of all files:\n{files}")

        if run_galaxy_importer and tarball.is_file():
            env = {}
            if galaxy_importer_config_path:
                env["GALAXY_IMPORTER_CONFIG"] = str(
                    Path(galaxy_importer_config_path).absolute()
                )
            with session.chdir(collection_dir):
                import_log = (
                    session.run(
                        "python",
                        "-m",
                        "galaxy_importer.main",
                        tarball.name,
                        env=env,
                        silent=True,
                    )
                    or ""
                )
            if import_log:
                with _ci_group("Run Galaxy importer"):
                    print(import_log)
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

    build_import_check.__doc__ = _compose_description(
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
