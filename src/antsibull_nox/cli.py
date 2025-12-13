# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# PYTHON_ARGCOMPLETE_OK

"""Entrypoint to the antsibull-docs script."""

from __future__ import annotations

import argparse
import os
import os.path
import sys
from collections.abc import Callable
from pathlib import Path

from . import __version__
from .cd import get_base_branch, get_changes, init_cd, supports_cd
from .config import CONFIG_FILENAME, load_config_from_toml
from .init import create_initial_config as _create_initial_config
from .lint_config import lint_config as _lint_config
from .sessions.utils.paths import PythonDependencies, add_python_deps

try:
    import argcomplete

    HAS_ARGCOMPLETE = True
except ImportError:
    HAS_ARGCOMPLETE = False


def lint_config(_: argparse.Namespace) -> int:
    """
    Lint antsibull-nox config file.
    """
    errors = _lint_config()
    for error in errors:
        print(error)
    return 0 if len(errors) == 0 else 3


def create_initial_config(_: argparse.Namespace) -> int:
    """
    Create noxfile.py and antsibull-nox.toml.
    """
    try:
        _create_initial_config()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    return 0


def show_changes(args: argparse.Namespace) -> int:
    """
    Show changes.
    """
    add_python_deps_opt: PythonDependencies = args.add_python_deps

    config_path = Path(CONFIG_FILENAME)
    cwd = Path.cwd()
    try:
        config = load_config_from_toml(config_path)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    try:
        init_cd(config=config, config_path=config_path, force=True)
        if not supports_cd():
            print(f"{config_path} does not support change detection.", file=sys.stderr)
            return 3

        base_branch = get_base_branch()
        changes = get_changes(relative_to=cwd) or []
    except ValueError as exc:
        print(f"Error while fetching changes: {exc}", file=sys.stderr)
        return 3

    original = set(changes)
    python_deps: set[Path] = set()
    python_appendum = ""

    changes_ex = list(changes)
    if add_python_deps_opt != "none":
        forward = add_python_deps_opt == "imported-by-changed"
        if forward:
            python_appendum = "transitive import by changed Python file"
        else:
            python_appendum = "transitively imports changed Python file"
        add_python_deps(changes_ex, forward=forward, cwd=cwd)
        python_deps = set(changes_ex) - original

    print(f"Changes with respect to {base_branch} branch:")
    if changes_ex:
        for file in sorted(changes_ex):
            appendums = []
            if file in python_deps:
                appendums.append(python_appendum)
            appendum = f" ({', '.join(appendums)})" if appendums else ""
            print(f" * {file}{appendum}")
    else:
        print("  (no changes found)")
    return 0


# Mapping from command line subcommand names to functions which implement those.
# The functions need to take a single argument, the processed list of args.
ARGS_MAP: dict[str, Callable[[argparse.Namespace], int]] = {
    "lint-config": lint_config,
    "init": create_initial_config,
    "show-changes": show_changes,
}


class InvalidArgumentError(Exception):
    """
    Error while parsing arguments.
    """


def parse_args(program_name: str, args: list[str]) -> argparse.Namespace:
    """
    Parse the command line arguments.
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

    subparsers.add_parser(
        "init",
        description="Create noxfile and antsibull-nox configuration file",
    )

    show_changes_parser = subparsers.add_parser(
        "show-changes", description="Show changed files"
    )
    show_changes_parser.add_argument(
        "--add-python-deps",
        default="none",
        choices=["none", "imported-by-changed", "importing-changed"],
        help="Include Python dependencies (forward or backward) for changed Python files."
        " If set to 'imported-by-changed', all Python files (transitively) importing"
        " changed files will be added ('backward'). If set to 'importing-changed', all"
        " Python files (transitively) imported by changed files will be added ('forward').",
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

    return ARGS_MAP[parsed_args.command](parsed_args)


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
