# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
CLI subcommand.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from semantic_version import Version

from ..cli_helper import FailCLIError, InvalidArgumentError
from ..collection.data import CollectionData
from ..collection.search import load_collection_data_from_disk
from ..config import Config, Releaser
from .base import BaseReleaser, VerifyFailed

_CANNOT_BE_USED_PREFIX = "This subcommand cannot be used because of: "
_NO_RELEASER_ERROR = "no releaser has been configured."


# pylint: disable-next=inconsistent-return-statements
def get_releaser(config: Releaser) -> BaseReleaser:
    """
    Create BaseReleaser instance.
    """
    if config.type == "zuul+github":
        # pylint: disable-next=import-outside-toplevel
        from .zuul_github import ZuulGitHubReleaser

        return ZuulGitHubReleaser(config)


def create_subcommand(releaser_parser: argparse.ArgumentParser, config: Config) -> None:
    """
    Fill the 'release' subcommand's parser with content.
    """
    if config.releaser is None:
        releaser_parser.epilog = f"{_CANNOT_BE_USED_PREFIX}Error: {_NO_RELEASER_ERROR}"
        return

    releaser = get_releaser(config.releaser)

    releaser_subparsers = releaser_parser.add_subparsers(
        title="Subcommands", dest="subcommand", help="for help use: `SUBCOMMANDS -h`"
    )
    releaser_subparsers.required = True

    vcs_release = releaser_subparsers.add_parser(
        "vcs-release",
        description="Create release in VCS.",
        help="Create release in VCS",
    )
    vcs_release.add_argument("version")

    extra_steps_needed = (
        "This should be disabled if extra steps are needed"
        " to build the Galaxy tarball from the sources."
    )

    wait = releaser_subparsers.add_parser(
        "wait",
        description="Wait until the release has been published.",
        help="Wait until the release has been published",
    )
    wait.add_argument("version")
    wait.add_argument(
        "--skip-validation",
        default=False,
        action="store_true",
        help="Do not validate the release (see 'validate' subcommand).",
    )
    wait.add_argument(
        "--skip-source-validation",
        default=False,
        action="store_true",
        help=f"When validating, do not validate the release's sources. {extra_steps_needed}",
    )

    validate = releaser_subparsers.add_parser(
        "validate",
        description="Validate that the release is published and its contents are as expected.",
        help="Validate that the release is published and its contents are as expected",
    )
    validate.add_argument("version")
    validate.add_argument(
        "--skip-source-validation",
        default=False,
        action="store_true",
        help=f"Do not validate the release's sources. {extra_steps_needed}",
    )

    if releaser.can_create_vcs_ui_release():
        create_vcs_ui_release = releaser_subparsers.add_parser(
            "create-vcs-ui-release",
            description="Create release in the VCS's UI.",
            help="Create release in the VCS's UI",
        )
        create_vcs_ui_release.add_argument("version")
        create_vcs_ui_release.add_argument(
            "--publish",
            default=False,
            action="store_true",
            help="Do not create a draft release.",
        )
        create_vcs_ui_release.add_argument(
            "--make-latest",
            default=False,
            action="store_true",
            help="Make the release 'latest'.",
        )
        create_vcs_ui_release.add_argument(
            "--skip-validation",
            default=False,
            action="store_true",
            help="Do not validate the release (see 'validate' subcommand).",
        )
        create_vcs_ui_release.add_argument(
            "--skip-source-validation",
            default=False,
            action="store_true",
            help=f"When validating, do not validate the release's sources. {extra_steps_needed}",
        )


def parse_version(version: str, *, name: str = "version") -> Version:
    """
    Parse semantic version
    """
    try:
        return Version(version)
    except ValueError as exc:
        raise InvalidArgumentError(
            f"Cannot parse {name} parameter {version!r}: {exc}"
        ) from exc


def cmd_vcs_release(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'vcs-release' subcommand.
    """
    v = parse_version(args.version)

    r = get_releaser(releaser)
    try:
        r.create_vcs_release(collection=collection, version=v)
        return 0
    except ValueError as exc:
        raise FailCLIError(f"Error: {exc}", code=3) from exc


def cmd_wait(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'wait' subcommand.
    """
    v = parse_version(args.version)
    skip_validation: bool = args.skip_validation
    skip_source_validation: bool = args.skip_source_validation

    r = get_releaser(releaser)
    try:
        r.wait_until_released(
            namespace=collection.namespace,
            name=collection.name,
            version=v,
            verify=not skip_validation,
            validate_with_sources=not skip_source_validation,
        )
        return 0
    except VerifyFailed as exc:
        raise FailCLIError(f"Verification failed: {exc}", code=4) from exc
    except ValueError as exc:
        raise FailCLIError(f"Error: {exc}", code=3) from exc


def cmd_validate(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'validate' subcommand.
    """
    v = parse_version(args.version)
    skip_source_validation: bool = args.skip_source_validation

    r = get_releaser(releaser)
    try:
        r.verify_release(
            namespace=collection.namespace,
            name=collection.name,
            version=v,
            validate_with_sources=not skip_source_validation,
        )
        return 0
    except VerifyFailed as exc:
        raise FailCLIError(f"Verification failed: {exc}", code=4) from exc
    except ValueError as exc:
        raise FailCLIError(f"Error: {exc}", code=3) from exc


def cmd_create_vcs_ui_release(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'wait' subcommand.
    """
    v = parse_version(args.version)
    skip_validation: bool = args.skip_validation
    skip_source_validation: bool = args.skip_source_validation
    publish: bool = args.publish
    make_latest: bool = args.make_latest
    if make_latest and v.prerelease:
        raise InvalidArgumentError("Cannot mark a pre-release as latest.")

    r = get_releaser(releaser)
    try:
        r.create_vcs_ui_release(
            namespace=collection.namespace,
            name=collection.name,
            version=v,
            make_draft=not publish,
            make_latest=make_latest,
            verify=not skip_validation,
            validate_with_sources=not skip_source_validation,
        )
        return 0
    except VerifyFailed as exc:
        raise FailCLIError(f"Verification failed: {exc}", code=4) from exc
    except ValueError as exc:
        raise FailCLIError(f"Error: {exc}", code=3) from exc


# Mapping from command line 'release' subcommand names to functions which implement those.
# The functions need to take a single argument, the processed list of args.
RELEASE_ARGS_MAP: dict[
    str, Callable[[argparse.Namespace, CollectionData, Config, Releaser], int]
] = {
    "vcs-release": cmd_vcs_release,
    "wait": cmd_wait,
    "validate": cmd_validate,
    "create-vcs-ui-release": cmd_create_vcs_ui_release,
}


def release_command(args: argparse.Namespace, config: Config) -> int:
    """
    Command for release subcommand, which is in turn a set of subcommands.
    """
    if config.releaser is None:
        raise FailCLIError(_NO_RELEASER_ERROR, code=3)

    collection_data = load_collection_data_from_disk(Path("."))

    try:
        return RELEASE_ARGS_MAP[args.subcommand](
            args, collection_data, config, config.releaser
        )
    except ValueError as exc:
        raise FailCLIError(f"{exc}", code=3) from exc


__all__ = ("create_subcommand", "release_command")
