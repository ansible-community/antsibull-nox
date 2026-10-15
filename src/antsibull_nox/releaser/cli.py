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

from ..cli_helper import FailCLIError, require_config
from ..config import Config, Releaser, create_config_not_found_error

_CANNOT_BE_USED_PREFIX = "This subcommand cannot be used because of: "
_NO_RELEASER_ERROR = "no releaser has been configured."


def create_subcommand(
    releaser_parser: argparse.ArgumentParser, config: Config | Exception | None
) -> None:
    """
    Fill the 'release' subcommand's parser with content.
    """
    if config is None:
        config = create_config_not_found_error()
    if isinstance(config, Exception):
        releaser_parser.epilog = f"{_CANNOT_BE_USED_PREFIX}Error: {config}"
        return
    if config.releaser is None:
        releaser_parser.epilog = f"{_CANNOT_BE_USED_PREFIX}Error: {_NO_RELEASER_ERROR}"
        return

    releaser_subparsers = releaser_parser.add_subparsers(
        title="Subcommands", dest="subcommand", help="for help use: `SUBCOMMANDS -h`"
    )
    releaser_subparsers.required = True

    # TODO


# Mapping from command line 'release' subcommand names to functions which implement those.
# The functions need to take a single argument, the processed list of args.
RELEASE_ARGS_MAP: dict[str, Callable[[argparse.Namespace, Config, Releaser], int]] = {
    # TODO
}


def release_command(args: argparse.Namespace, config: Config | Exception | None) -> int:
    """
    Command for release subcommand, which is in turn a set of subcommands.
    """
    config = require_config(config)
    if config.releaser is None:
        raise FailCLIError(_NO_RELEASER_ERROR, code=3)

    try:
        return RELEASE_ARGS_MAP[args.subcommand](args, config, config.releaser)
    except ValueError as exc:
        raise FailCLIError(f"{exc}", code=3) from exc


__all__ = ("create_subcommand", "release_command")
