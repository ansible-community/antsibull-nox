# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Changelog helpers.
"""

from __future__ import annotations

import argparse
import datetime

from antsibull_changelog.changes import add_release, load_changes
from antsibull_changelog.cli import _determine_flatmap, _do_refresh
from antsibull_changelog.config import (
    ChangelogConfig,
    CollectionDetails,
    PathsConfig,
)
from antsibull_changelog.errors import ChangelogError
from antsibull_changelog.fragment import (
    ChangelogFragment,
    ChangelogFragmentLinter,
    load_fragments,
)
from antsibull_changelog.logger import setup_logger
from antsibull_changelog.plugins import load_plugins
from antsibull_changelog.rendering.changelog import generate_changelog
from semantic_version import Version


def lint_fragments(
    config: ChangelogConfig,
    fragments: list[ChangelogFragment],
) -> bool:
    """
    Run linter on a given set of changelog fragment objects, and return ``True`` if all pass.
    """
    linter = ChangelogFragmentLinter(config)
    for fragment in fragments:
        if linter.lint(fragment):
            return False
    return True


def make_release(
    version: Version,
    *,
    cummulative_release: bool = False,
    ansible_doc_bin: str | None = None,
    date: datetime.date | None = None,
) -> None:
    """
    Equivalent of running 'antsibull-changelog release'.
    """
    setup_logger(0)

    if date is None:
        date = datetime.date.today()

    try:
        paths = PathsConfig.force_collection(".", ansible_doc_bin=ansible_doc_bin)
        collection_details = CollectionDetails(paths)
        config = ChangelogConfig.load(paths, collection_details)

        flatmap = _determine_flatmap(collection_details, config)

        codename = None

        changes = load_changes(config)
        if str(version) in changes.releases:
            raise ValueError(f"{version} has already been released!")

        prev_version: str | None = None
        if cummulative_release:
            prev_version = (
                changes.latest_version if changes.has_release else changes.ancestor
            )

        plugins = load_plugins(
            paths=paths,
            collection_details=collection_details,
            config=config,
            version=str(version),
            force_reload=True,
            use_ansible_doc=False,
            add_plugin_period=config.add_plugin_period,
        )
        fragments = load_fragments(paths, config)
        if not lint_fragments(config, fragments):
            raise ValueError(
                "Please fix all linting errors before releasing a new version! "
                "Use `antsibull-changelog lint` to manually lint before releasing."
            )

        if not any("release_summary" in fragment.content for fragment in fragments):
            raise ValueError(
                f"There is no release_summary for {version} in the changelog fragments."
            )

        args = argparse.Namespace(
            refresh_plugins=None,
            refresh_fragments=None,
            refresh=False,
            reload_plugins=True,
            use_ansible_doc=False,
        )
        plugins, fragments = _do_refresh(
            args, paths, collection_details, config, changes, plugins, fragments
        )
        add_release(
            config,
            changes,
            plugins,
            fragments,
            str(version),
            codename,
            date,
            update_existing=True,
            prev_version=prev_version,
            objects=plugins,
        )
        for output in config.output:
            generate_changelog(
                paths,
                config,
                changes,
                output,
                flatmap=flatmap,
            )
    except ChangelogError as exc:
        raise ValueError(f"Error while adding release to changelog: {exc}") from exc


__all__ = ("make_release",)
