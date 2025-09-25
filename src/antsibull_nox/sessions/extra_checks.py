# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox extra checks session.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import nox

from .utils import (
    compose_description,
)
from .utils.scripts import (
    run_bare_script,
)


@dataclass
class ActionGroup:
    """
    Defines an action group.
    """

    # Name of the action group.
    name: str
    # Regex pattern to match modules that could belong to this action group.
    pattern: str
    # Doc fragment that members of the action group must have, but no other module
    # must have
    doc_fragment: str
    # Exclusion list of modules that match the regex, but should not be part of the
    # action group. All other modules matching the regex are assumed to be part of
    # the action group.
    exclusions: list[str] | None = None


@dataclass
class AvoidCharacterGroup:  # pylint: disable=too-many-instance-attributes
    """
    Defines an avoid character group.
    """

    # User-friendly name
    name: str | None
    # Regular expression
    regex: str
    # Extensions, paths, and directories to look for.
    # If None (not specified), will consider all files.
    match_extensions: list[str] | None
    match_paths: list[str] | None
    match_directories: list[str] | None
    # Extensions, paths, and directories to skip.
    skip_extensions: list[str]
    skip_paths: list[str]
    skip_directories: list[str]


def add_extra_checks(
    *,
    make_extra_checks_default: bool = True,
    # no-unwanted-files:
    run_no_unwanted_files: bool = True,
    no_unwanted_files_module_extensions: (
        list[str] | None
    ) = None,  # default: .cs, .ps1, .psm1, .py
    no_unwanted_files_other_extensions: list[str] | None = None,  # default: .py, .pyi
    no_unwanted_files_yaml_extensions: list[str] | None = None,  # default: .yml, .yaml
    no_unwanted_files_skip_paths: list[str] | None = None,  # default: []
    no_unwanted_files_skip_directories: list[str] | None = None,  # default: []
    no_unwanted_files_yaml_directories: (
        list[str] | None
    ) = None,  # default: plugins/test/, plugins/filter/
    no_unwanted_files_allow_symlinks: bool = False,
    # action-groups:
    run_action_groups: bool = False,
    action_groups_config: list[ActionGroup] | None = None,
    # no-trailing-whitespace:
    run_no_trailing_whitespace: bool = False,
    no_trailing_whitespace_skip_paths: list[str] | None = None,
    no_trailing_whitespace_skip_directories: list[str] | None = None,
    # avoid-character-group:
    run_avoid_characters: bool = False,
    avoid_character_group: list[AvoidCharacterGroup] | None = None,
) -> None:
    """
    Add extra-checks session for extra checks.
    """

    def execute_no_unwanted_files(session: nox.Session) -> None:
        run_bare_script(
            session,
            "no-unwanted-files",
            extra_data={
                "module_extensions": no_unwanted_files_module_extensions
                or [".cs", ".ps1", ".psm1", ".py"],
                "other_extensions": no_unwanted_files_other_extensions
                or [".py", ".pyi"],
                "yaml_extensions": no_unwanted_files_yaml_extensions
                or [".yml", ".yaml"],
                "skip_paths": no_unwanted_files_skip_paths or [],
                "skip_directories": no_unwanted_files_skip_directories or [],
                "yaml_directories": no_unwanted_files_yaml_directories
                or ["plugins/test/", "plugins/filter/"],
                "allow_symlinks": no_unwanted_files_allow_symlinks,
            },
            with_cd=True,
        )

    def execute_action_groups(session: nox.Session) -> None:
        if action_groups_config is None:
            session.warn("Skipping action-groups since config is not provided...")
            return
        run_bare_script(
            session,
            "action-groups",
            extra_data={
                "config": [asdict(cfg) for cfg in action_groups_config],
            },
            with_cd=True,
        )

    def execute_no_trailing_whitespace(session: nox.Session) -> None:
        run_bare_script(
            session,
            "no-trailing-whitespace",
            extra_data={
                "skip_paths": no_trailing_whitespace_skip_paths or [],
                "skip_directories": no_trailing_whitespace_skip_directories or [],
            },
            with_cd=True,
        )

    def execute_avoid_characters(session: nox.Session) -> None:
        if avoid_character_group is None:
            session.warn("Skipping avoid-characters since config is not provided...")
            return
        run_bare_script(
            session,
            "avoid-characters",
            extra_data={
                "config": [asdict(cfg) for cfg in avoid_character_group],
            },
            with_cd=True,
        )

    def extra_checks(session: nox.Session) -> None:
        if run_no_unwanted_files:
            execute_no_unwanted_files(session)
        if run_action_groups:
            execute_action_groups(session)
        if run_no_trailing_whitespace:
            execute_no_trailing_whitespace(session)
        if run_avoid_characters:
            execute_avoid_characters(session)

    extra_checks.__doc__ = compose_description(
        prefix={
            "one": "Run extra checker:",
            "other": "Run extra checkers:",
        },
        programs={
            "no-unwanted-files": (
                "checks for unwanted files in plugins/"
                if run_no_unwanted_files
                else False
            ),
            "action-groups": "validate action groups" if run_action_groups else False,
            "no-trailing-whitespace": (
                "avoid trailing whitespace" if run_no_trailing_whitespace else False
            ),
            "avoid-character-groups": (
                "avoid characters" if run_avoid_characters else False
            ),
        },
    )
    nox.session(
        name="extra-checks",
        python=False,
        default=make_extra_checks_default,
    )(extra_checks)


__all__ = [
    "ActionGroup",
    "add_extra_checks",
]
