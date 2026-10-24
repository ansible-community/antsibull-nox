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
from ..config import (
    CONFIG_FILENAME,
    Config,
    Releaser,
    VersionBump,
    VersionBumpValues,
    load_config_from_toml_data,
)
from .base import BaseReleaser, VerifyFailed
from .ui import log

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


def get_actual_releaser(config: Releaser, *, version: Version) -> BaseReleaser:
    """
    Create BaseReleaser instance from the repository's state at release ``version``.
    """
    r = get_releaser(config)
    exists, config_contents = r.get_config_file_from_release(version=version)
    if not exists:
        raise FailCLIError(f"The release {version} does not exist!", code=3)
    if config_contents is None:
        raise FailCLIError(
            f"The release {version} does not have a {CONFIG_FILENAME} configuration file!",
            code=3,
        )
    try:
        antsibull_nox_config = load_config_from_toml_data(
            path=CONFIG_FILENAME, content=config_contents
        )
    except Exception as exc:
        raise FailCLIError(
            f"Error when loading {CONFIG_FILENAME} for release {version}: {exc}", code=3
        ) from exc
    new_config = antsibull_nox_config.releaser
    if new_config is None:
        raise FailCLIError(
            f"{CONFIG_FILENAME} for release {version} does not specify a releaser",
            code=3,
        )
    if new_config.type != config.type:
        raise FailCLIError(
            f"{CONFIG_FILENAME} for release {version} specifies a different releaser"
            " than the current repository state",
            code=3,
        )
    if new_config != config:
        log(f"Reloading releaser configuration for release {version}.")
    return get_releaser(new_config)


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

    vcs_prepare = releaser_subparsers.add_parser(
        "vcs-prepare",
        description="Prepare a release in VCS.",
        help="Prepare a release in VCS",
    )
    vcs_prepare.add_argument("version")
    vcs_prepare.add_argument(
        "-m", "--message", required=True, help="The release summary."
    )

    vcs_release = releaser_subparsers.add_parser(
        "vcs-release",
        description="Create release in VCS.",
        help="Create release in VCS",
    )
    vcs_release.add_argument("version")

    vcs_bump_version = releaser_subparsers.add_parser(
        "vcs-bump-version",
        description="Bump version in VCS.",
        help="Bump version in VCS",
    )
    vcs_bump_version.add_argument("--new-version", help="The new version.")
    vcs_bump_version.add_argument(
        "--bump",
        choices=VersionBumpValues,
        help=(
            "How to obtain the new version from the current version."
            " 'next-major': increase the major part;"
            " 'next-minor': increase the minor part;"
            " 'next-bugfix': increase the bugfix part;"
            " 'post-prerelease': append 'post0' to the prerelease part."
        ),
    )
    vcs_bump_version.add_argument("--message", "-m", help="The commit message.")
    vcs_bump_version.epilog = """\
At most one of --new-version and --bump must be specified.
If none is specified, the bump method must be configured in the releaser config.

Also if --message is not specified, a commit message must be configured in the releaser config.
"""

    extra_steps_needed = (
        "This should be disabled if extra steps are needed"
        " to build the Galaxy tarball from the sources."
    )

    load_release_config_epilog = (
        "Antsibull-nox will reload its config from the repository state of the release"
        " for this subcommand."
        " It will fail if the releaser configuration at that state is too different"
        " from the current releaser configuration."
    )

    release = releaser_subparsers.add_parser(
        "release",
        description="Initiate release from the local release in VCS.",
        help="Initiate release from the local release in VCS",
    )
    release.epilog = load_release_config_epilog
    release.add_argument("version")
    release.add_argument(
        "--skip-validation",
        default=False,
        action="store_true",
        help="Do not validate the release (see 'validate' subcommand). This should not be used.",
    )
    release.add_argument(
        "--skip-source-validation",
        default=False,
        action="store_true",
        help=f"When validating, do not validate the release's sources. {extra_steps_needed}",
    )
    if releaser.can_create_vcs_ui_release():
        release.add_argument(
            "--publish",
            default=False,
            action="store_true",
            help="Do not create a draft release.",
        )
        release.add_argument(
            "--make-latest",
            default=False,
            action="store_true",
            help="Make the release 'latest'.",
        )
        release.add_argument(
            "--without-token",
            default=False,
            action="store_true",
            help="Do not use an API token. Will fail if this is not possible.",
        )

    wait = releaser_subparsers.add_parser(
        "wait",
        description="Wait until the release has been published.",
        help="Wait until the release has been published",
    )
    wait.epilog = load_release_config_epilog
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
    validate.epilog = load_release_config_epilog
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
        create_vcs_ui_release.epilog = load_release_config_epilog
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
        create_vcs_ui_release.add_argument(
            "--without-token",
            default=False,
            action="store_true",
            help="Do not use an API token. Will fail if this is not possible.",
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


def cmd_vcs_prepare(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'vcs-release' subcommand.
    """
    v = parse_version(args.version)
    message: str = args.message

    r = get_releaser(releaser)
    r.prepare_vcs_release(collection=collection, version=v, release_summary=message)
    log(f"The {v} release has been prepared.")
    return 0


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
    r.create_vcs_release(collection=collection, version=v)
    log(f"The {v} release has been created.")
    return 0


def cmd_vcs_bump_version(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'vcs-release' subcommand.
    """
    new_version = (
        parse_version(args.new_version) if args.new_version is not None else None
    )
    bump: VersionBump | None = args.bump
    message: str | None = args.message

    r = get_releaser(releaser)
    actual_new_version = r.bump_version(
        collection=collection,
        new_version=new_version,
        bump=bump,
        commit_message=message,
    )
    if actual_new_version is not None:
        log(f"Version bumped to {actual_new_version}")
    else:
        log("Version was already set.")
    return 0


def cmd_release(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'release' subcommand.
    """
    v = parse_version(args.version)
    skip_validation: bool = args.skip_validation
    skip_source_validation: bool = args.skip_source_validation
    r = get_actual_releaser(releaser, version=v)
    if r.can_create_vcs_ui_release():
        publish: bool = args.publish
        make_latest: bool = args.make_latest
        without_token: bool = args.without_token
        if make_latest and v.prerelease:
            raise InvalidArgumentError("Cannot mark a pre-release as latest.")
    else:
        publish = False
        make_latest = False
        without_token = True

    url = r.publish_release(
        namespace=collection.namespace,
        name=collection.name,
        version=v,
        make_draft=not publish,
        make_latest=make_latest,
        verify=not skip_validation,
        validate_with_sources=not skip_source_validation,
        without_token=without_token,
    )
    if r.can_create_vcs_ui_release():
        if url is not None:
            log(f"The collection has been published; VCS release available at: {url}")
        else:
            log("The collection has been published; VCS release has been created.")
    else:
        log("The collection has been published.")
    return 0


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

    r = get_actual_releaser(releaser, version=v)
    r.wait_until_released(
        namespace=collection.namespace,
        name=collection.name,
        version=v,
        verify=not skip_validation,
        validate_with_sources=not skip_source_validation,
    )
    log("The release has been published!")
    return 0


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

    r = get_actual_releaser(releaser, version=v)
    r.verify_release(
        namespace=collection.namespace,
        name=collection.name,
        version=v,
        validate_with_sources=not skip_source_validation,
    )
    return 0


def cmd_create_vcs_ui_release(
    args: argparse.Namespace,
    collection: CollectionData,
    _config: Config,
    releaser: Releaser,
) -> int:
    """
    The 'create-vcs-ui-release' subcommand.
    """
    v = parse_version(args.version)
    skip_validation: bool = args.skip_validation
    skip_source_validation: bool = args.skip_source_validation
    publish: bool = args.publish
    make_latest: bool = args.make_latest
    without_token: bool = args.without_token
    if make_latest and v.prerelease:
        raise InvalidArgumentError("Cannot mark a pre-release as latest.")

    r = get_actual_releaser(releaser, version=v)
    url = r.create_vcs_ui_release(
        namespace=collection.namespace,
        name=collection.name,
        version=v,
        make_draft=not publish,
        make_latest=make_latest,
        verify=not skip_validation,
        validate_with_sources=not skip_source_validation,
        without_token=without_token,
    )
    if url is not None:
        log(f"VCS release available at: {url}")
    else:
        log("VCS release has been created.")
    return 0


# Mapping from command line 'release' subcommand names to functions which implement those.
# The functions need to take a single argument, the processed list of args.
RELEASE_ARGS_MAP: dict[
    str, Callable[[argparse.Namespace, CollectionData, Config, Releaser], int]
] = {
    "vcs-prepare": cmd_vcs_prepare,
    "vcs-release": cmd_vcs_release,
    "vcs-bump-version": cmd_vcs_bump_version,
    "release": cmd_release,
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
    except VerifyFailed as exc:
        raise FailCLIError(f"Verification failed: {exc}", code=4) from exc
    except ValueError as exc:
        raise FailCLIError(f"Error: {exc}", code=3) from exc


__all__ = ("create_subcommand", "release_command")
