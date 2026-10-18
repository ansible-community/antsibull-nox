# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
CLI subcommand (lazy import).
"""

from __future__ import annotations

import argparse

from ..cli_helper import FailCLIError, require_config
from ..config import Config, create_config_not_found_error

_CANNOT_BE_USED_PREFIX = "This subcommand cannot be used because of: "
_NO_RELEASER_ERROR = "no releaser has been configured."
_MISSING_REQUIREMENTS = (
    "the necessary requirements are missing."
    " Please install antsibull-nox with the [releaser] dependency group."
)


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

    try:
        # pylint: disable-next=import-outside-toplevel
        from .cli import create_subcommand as create_subcommand_impl
    except ImportError:
        releaser_parser.epilog = (
            f"{_CANNOT_BE_USED_PREFIX}Error: {_MISSING_REQUIREMENTS}"
        )
        return

    create_subcommand_impl(releaser_parser, config)


def release_command(args: argparse.Namespace, config: Config | Exception | None) -> int:
    """
    Command for release subcommand, which is in turn a set of subcommands.
    """
    config = require_config(config)
    if config.releaser is None:
        raise FailCLIError(_NO_RELEASER_ERROR, code=3)

    try:
        # pylint: disable-next=import-outside-toplevel
        from .cli import release_command as release_command_impl
    except ImportError as exc:
        raise FailCLIError(_MISSING_REQUIREMENTS, code=3) from exc

    return release_command_impl(args, config)


__all__ = ("create_subcommand", "release_command")
