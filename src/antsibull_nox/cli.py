# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020, Ansible Project

# PYTHON_ARGCOMPLETE_OK

"""Entrypoint to the antsibull-docs script."""

from __future__ import annotations

import argparse
import os
import os.path
import sys
from collections.abc import Callable

from . import __version__
from .config import lint_config_toml

try:
    import argcomplete

    HAS_ARGCOMPLETE = True
except ImportError:
    HAS_ARGCOMPLETE = False


def lint_config() -> int:
    """
    Lint antsibull-nox config file.
    """
    errors = lint_config_toml()
    for error in errors:
        print(error)
    return 0 if len(errors) == 0 else 3


#: Mapping from command line subcommand names to functions which implement those
#: The functions need to take a single argument, the processed list of args.
ARGS_MAP: dict[str, Callable[[], int]] = {
    "lint-config": lint_config,
}


class InvalidArgumentError(Exception):
    """
    Error while parsing arguments.
    """


def parse_args(program_name: str, args: list[str]) -> argparse.Namespace:
    """
    Parse and coerce the command line arguments.
    """

    toplevel_parser = argparse.ArgumentParser(
        prog=program_name,
        description="Script to manage generated documentation for ansible",
    )
    toplevel_parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Print the antsibull-nox version",
    )
    subparsers = toplevel_parser.add_subparsers(
        title="Subcommands", dest="command", help="for help use: `SUBCOMMANDS -h`"
    )
    subparsers.required = True

    subparsers.add_parser(
        "lint-config",
        description="Lint antsibull-nox configuration file",
    )

    # This must come after all parser setup
    if HAS_ARGCOMPLETE:
        argcomplete.autocomplete(toplevel_parser)

    parsed_args: argparse.Namespace = toplevel_parser.parse_args(args)
    return parsed_args


def run(args: list[str]) -> int:
    """
    Run the program.
    """
    program_name = os.path.basename(args[0])
    try:
        parsed_args: argparse.Namespace = parse_args(program_name, args[1:])
    except InvalidArgumentError as e:
        print(e, file=sys.stderr)
        return 2

    return ARGS_MAP[parsed_args.command]()


def main() -> int:
    """
    Entrypoint called from the script.

    Return codes:
        :0: Success
        :1: Unhandled error.  See the Traceback for more information.
        :2: There was a problem with the command line arguments
    """
    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
