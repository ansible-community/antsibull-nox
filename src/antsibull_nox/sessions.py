# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox sessions.
"""

from __future__ import annotations

import contextlib
import functools
import os
import shlex
import subprocess
import sys
import typing as t
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import nox
from antsibull_fileutils.vcs import detect_vcs, list_git_files

from .collection import (
    CollectionData,
    setup_collections,
    setup_current_tree,
)
from .data_util import prepare_data_script

IN_CI = "GITHUB_ACTIONS" in os.environ
ALLOW_EDITABLE = os.environ.get("ALLOW_EDITABLE", str(not IN_CI)).lower() in (
    "1",
    "true",
)

COLLECTION_NAME = "community.dns"

CODE_FILES = [
    "plugins",
    "tests/unit",
]

MODULE_PATHS = [
    "plugins/modules/",
    "plugins/module_utils/",
    "tests/unit/plugins/modules/",
    "tests/unit/plugins/module_utils/",
]


def find_data_directory() -> Path:
    """
    Retrieve the directory for antsibull_nox.data on disk.
    """
    return Path(__file__).parent / "data"


def install(session: nox.Session, *args: str, editable: bool = False, **kwargs):
    """
    Install Python packages.
    """
    # nox --no-venv
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn(f"No venv. Skipping installation of {args}")
        return
    # Don't install in editable mode in CI or if it's explicitly disabled.
    # This ensures that the wheel contains all of the correct files.
    if editable and ALLOW_EDITABLE:
        args = ("-e", *args)
    session.install(*args, "-U", **kwargs)


@dataclass
class CollectionSetup:
    """
    Information on the setup collections.
    """

    # The path of the ansible_collections directory where all dependent collections
    # are installed. Is currently identical to current_root, but that might change
    # or depend on options in the future.
    collections_root: Path

    # The directory in which ansible_collections can be found, as well as
    # ansible_collections/<namespace>/<name> points to a copy of the current collection.
    current_place: Path

    # The path of the ansible_collections directory that contains the current collection.
    # The following is always true:
    #   current_root == current_place / "ansible_collections"
    current_root: Path

    # Data on the current collection (as in the repository).
    current_collection: CollectionData

    # The path of the current collection inside the collection tree below current_root.
    # The following is always true:
    #   current_path == current_root / current_collection.namespace / current_collection.name
    current_path: Path

    def prefix_current_paths(self, paths: list[str]) -> list[str]:
        """
        Prefix the list of given paths with ``current_path``.
        """
        result = []
        for path in paths:
            prefixed_path = (self.current_path / path).relative_to(self.current_place)
            if prefixed_path.exists():
                result.append(str(prefixed_path))
        return result


def _run_subprocess(args: list[str]) -> tuple[bytes, bytes]:
    p = subprocess.run(args, check=True, capture_output=True)
    return p.stdout, p.stderr


def prepare_collections(
    session: nox.Session,
    *,
    extra_deps_files: list[str | os.PathLike] | None = None,
    extra_collections: list[str] | None = None,
) -> CollectionSetup | None:
    """
    Install collections in site-packages.
    """
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn("No venv. Skip preparing collections...")
        return None
    place = Path(session.virtualenv.location) / "collection-root"
    place.mkdir(exist_ok=True)
    setup = setup_collections(
        place,
        _run_subprocess,
        extra_deps_files=extra_deps_files,
        extra_collections=extra_collections,
        with_current=False,
    )
    current_setup = setup_current_tree(place, setup.current_collection)
    return CollectionSetup(
        collections_root=setup.root,
        current_place=place,
        current_root=current_setup.root,
        current_collection=setup.current_collection,
        current_path=t.cast(Path, current_setup.current_path),
    )


@contextlib.contextmanager
def ansible_collection_root() -> Generator[tuple[str, str]]:
    """
    Context manager that changes to the root directory and yields the path of
    the root directory and the prefix to the current working directory from the root.
    """
    cwd = os.getcwd()
    root = os.path.normpath(os.path.join(cwd, "..", "..", ".."))
    try:
        os.chdir(root)
        yield root, os.path.relpath(cwd, root)
    finally:
        os.chdir(cwd)


def prefix_paths(paths: list[str], /, prefix: str) -> list[str]:
    """
    Prefix paths with the given prefix.
    """
    return [os.path.join(prefix, path) for path in paths]


def match_path(path: str, is_file: bool, paths: list[str]) -> bool:
    """
    Check whether a path (that is a file or not) matches a given list of paths.
    """
    for check in paths:
        if check == path:
            return True
        if not is_file:
            if not check.endswith("/"):
                check += "/"
            if path.startswith(check):
                return True
    return False


def restrict_paths(paths: list[str], restrict: list[str]) -> list[str]:
    """
    Restrict a list of paths with a given set of restrictions.
    """
    result = []
    for path in paths:
        is_file = os.path.isfile(path)
        if not is_file and not path.endswith("/"):
            path += "/"
        if not match_path(path, is_file, restrict):
            if not is_file:
                for check in restrict:
                    if check.startswith(path) and os.path.exists(check):
                        result.append(check)
            continue
        result.append(path)
    return result


def _scan_remove_paths(
    path: str, remove: list[str], extensions: list[str] | None
) -> list[str]:
    result = []
    for root, dirs, files in os.walk(path, topdown=True):
        if not root.endswith("/"):
            root += "/"
        if match_path(root, False, remove):
            continue
        if all(not check.startswith(root) for check in remove):
            dirs[:] = []
            result.append(root)
            continue
        for file in files:
            if extensions and os.path.splitext(file)[1] not in extensions:
                continue
            filepath = os.path.normpath(os.path.join(root, file))
            if not match_path(filepath, True, remove):
                result.append(filepath)
        for directory in list(dirs):
            if directory == "__pycache__":
                continue
            dirpath = os.path.normpath(os.path.join(root, directory))
            if match_path(dirpath, False, remove):
                dirs.remove(directory)
                continue
    return result


def remove_paths(
    paths: list[str], remove: list[str], extensions: list[str] | None
) -> list[str]:
    """
    Restrict a list of paths by removing paths.

    If ``extensions`` is specified, only files matching this extension
    will be considered when files need to be explicitly enumerated.
    """
    result = []
    for path in paths:
        is_file = os.path.isfile(path)
        if not is_file and not path.endswith("/"):
            path += "/"
        if match_path(path, is_file, remove):
            continue
        if not is_file and any(check.startswith(path) for check in remove):
            result.extend(_scan_remove_paths(path, remove, extensions))
            continue
        result.append(path)
    return result


def filter_paths(
    paths: list[str],
    /,
    remove: list[str] | None = None,
    restrict: list[str] | None = None,
    extensions: list[str] | None = None,
) -> list[str]:
    """
    Modifies a list of paths by restricting to and/or removing paths.
    """
    if restrict:
        paths = restrict_paths(paths, restrict)
    if remove:
        paths = remove_paths(paths, remove, extensions)
    return [path for path in paths if os.path.exists(path)]


@functools.cache
def list_all_files() -> list[Path]:
    """
    List all files of interest in the repository.
    """
    directory = Path.cwd()
    vcs = detect_vcs(directory)
    if vcs == "git":
        return [directory / path.decode("utf-8") for path in list_git_files(directory)]
    result = []
    for root, dirs, files in os.walk(directory, topdown=True):
        root_path = Path(root)
        for file in files:
            result.append(root_path / file)
        if root_path == directory and ".nox" in dirs:
            dirs.remove(".nox")
    return result


def add_lint(has_formatters: bool, has_codeqa: bool, has_typing: bool) -> None:
    """
    Add nox meta session for linting.
    """

    def lint(session: nox.Session) -> None:  # pylint: disable=unused-argument
        pass  # this session is deliberately empty

    dependent_sessions = []
    if has_formatters:
        dependent_sessions.append("formatters")
    if has_codeqa:
        dependent_sessions.append("codeqa")
    if has_typing:
        dependent_sessions.append("typing")
    nox.session(lint, name="lint", default=True, requires=dependent_sessions)  # type: ignore


def add_formatters(
    *,
    # isort:
    run_isort: bool,
    isort_config: str | os.PathLike | None,
    isort_package: str,
    # black:
    run_black: bool,
    run_black_modules: bool | None,
    black_config: str | os.PathLike | None,
    black_package: str,
) -> None:
    """
    Add nox session for formatters.
    """
    if run_black_modules is None:
        run_black_modules = run_black
    run_check = IN_CI

    def compose_dependencies() -> list[str]:
        deps = []
        if run_isort:
            deps.append(isort_package)
        if run_black or run_black_modules:
            deps.append(black_package)
        return deps

    def execute_isort(session: nox.Session) -> None:
        command: list[str] = [
            "isort",
        ]
        if run_check:
            command.append("--check")
        if isort_config is not None:
            command.extend(["--settings-file", str(isort_config)])
        command.extend(session.posargs)
        command.extend(filter_paths(CODE_FILES + ["noxfile.py"]))
        session.run(*command)

    def execute_black_for(session: nox.Session, paths: list[str]) -> None:
        if not paths:
            return
        command = ["black"]
        if black_config is not None:
            command.extend(["--config", str(black_config)])
        command.extend(session.posargs)
        command.extend(paths)
        session.run(*command)

    def execute_black(session: nox.Session) -> None:
        if run_black and run_black_modules:
            execute_black_for(session, filter_paths(CODE_FILES + ["noxfile.py"]))
            return
        if run_black:
            paths = filter_paths(
                CODE_FILES,
                remove=MODULE_PATHS,
                extensions=[".py"],
            ) + ["noxfile.py"]
            execute_black_for(session, paths)
        if run_black_modules:
            paths = filter_paths(
                CODE_FILES,
                restrict=MODULE_PATHS,
                extensions=[".py"],
            )
            execute_black_for(session, paths)

    def formatters(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        if run_isort:
            execute_isort(session)
        if run_black or run_black_modules:
            execute_black(session)

    nox.session(formatters, name="formatters", default=False)  # type: ignore


def add_codeqa(  # noqa: C901
    *,
    # flake8:
    run_flake8: bool,
    flake8_config: str | os.PathLike | None,
    flake8_package: str,
    # pylint:
    run_pylint: bool,
    pylint_rcfile: str | os.PathLike | None,
    pylint_modules_rcfile: str | os.PathLike | None,
    pylint_package: str,
    pylint_ansible_core_package: str | None,
    pylint_extra_deps: list[str],
) -> None:
    """
    Add nox session for codeqa.
    """

    def compose_dependencies() -> list[str]:
        deps = []
        if run_flake8:
            deps.append(flake8_package)
        if run_pylint:
            deps.append(pylint_package)
            if pylint_ansible_core_package is not None:
                deps.append(pylint_ansible_core_package)
            if os.path.isdir("tests/unit"):
                deps.append("pytest")
                if os.path.isfile("tests/unit/requirements.txt"):
                    deps.extend(["-r", "tests/unit/requirements.txt"])
            for extra_dep in pylint_extra_deps:
                deps.extend(shlex.split(extra_dep))
        return deps

    def execute_flake8(session: nox.Session) -> None:
        command: list[str] = [
            "flake8",
        ]
        if flake8_config is not None:
            command.extend(["--config", str(flake8_config)])
        command.extend(session.posargs)
        command.extend(filter_paths(CODE_FILES + ["noxfile.py"]))
        session.run(*command)

    def execute_pylint_impl(
        session: nox.Session,
        prepared_collections: CollectionSetup,
        config: os.PathLike | str | None,
        paths: list[str],
    ) -> None:
        command = ["pylint"]
        if config is not None:
            command.extend(
                [
                    "--rcfile",
                    os.path.join(prepared_collections.current_collection.path, config),
                ]
            )
        command.extend(["--source-roots", "."])
        command.extend(session.posargs)
        command.extend(prepared_collections.prefix_current_paths(paths))
        session.run(*command)

    def execute_pylint(
        session: nox.Session, prepared_collections: CollectionSetup
    ) -> None:
        if pylint_modules_rcfile is not None and pylint_modules_rcfile != pylint_rcfile:
            # Only run pylint twice when using different configurations
            module_paths = filter_paths(
                CODE_FILES, restrict=MODULE_PATHS, extensions=[".py"]
            )
            other_paths = filter_paths(
                CODE_FILES, remove=MODULE_PATHS, extensions=[".py"]
            )
        else:
            # Otherwise run it only once using the general configuration
            module_paths = []
            other_paths = filter_paths(CODE_FILES)

        with session.chdir(prepared_collections.current_place):
            if module_paths:
                execute_pylint_impl(
                    session,
                    prepared_collections,
                    pylint_modules_rcfile or pylint_rcfile,
                    module_paths,
                )

            if other_paths:
                execute_pylint_impl(
                    session, prepared_collections, pylint_rcfile, other_paths
                )

    def codeqa(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        prepared_collections: CollectionSetup | None = None
        if run_pylint:
            prepared_collections = prepare_collections(
                session, extra_deps_files=["tests/unit/requirements.yml"]
            )
            if not prepared_collections:
                session.warn("Skipping pylint...")
        if run_flake8:
            execute_flake8(session)
        if run_pylint and prepared_collections:
            execute_pylint(session, prepared_collections)

    nox.session(codeqa, name="codeqa", default=False)  # type: ignore


def add_typing(
    *,
    run_mypy: bool,
    mypy_config: str | os.PathLike | None,
    mypy_package: str,
    mypy_ansible_core_package: str | None,
    mypy_extra_deps: list[str],
) -> None:
    """
    Add nox session for typing.
    """

    def compose_dependencies() -> list[str]:
        deps = []
        if run_mypy:
            deps.append(mypy_package)
            if mypy_ansible_core_package is not None:
                deps.append(mypy_ansible_core_package)
            if os.path.isdir("tests/unit"):
                deps.append("pytest")
                if os.path.isfile("tests/unit/requirements.txt"):
                    deps.extend(["-r", "tests/unit/requirements.txt"])
            for extra_dep in mypy_extra_deps:
                deps.extend(shlex.split(extra_dep))
        return deps

    def execute_mypy(
        session: nox.Session, prepared_collections: CollectionSetup
    ) -> None:
        # Run mypy
        with session.chdir(prepared_collections.current_place):
            command = ["mypy"]
            if mypy_config is not None:
                command.extend(
                    [
                        "--config-file",
                        os.path.join(
                            prepared_collections.current_collection.path, mypy_config
                        ),
                    ]
                )
            command.append("--namespace-packages")
            command.append("--explicit-package-bases")
            command.extend(session.posargs)
            command.extend(prepared_collections.prefix_current_paths(CODE_FILES))
            session.run(
                *command, env={"MYPYPATH": str(prepared_collections.current_place)}
            )

    def typing(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        prepared_collections = prepare_collections(
            session, extra_deps_files=["tests/unit/requirements.yml"]
        )
        if not prepared_collections:
            session.warn("Skipping mypy...")
        if run_mypy and prepared_collections:
            execute_mypy(session, prepared_collections)

    nox.session(typing, name="typing", default=False)  # type: ignore


def add_lint_sessions(
    *,
    # isort:
    run_isort: bool = True,
    isort_config: str | os.PathLike | None = None,
    isort_package: str = "isort",
    # black:
    run_black: bool = True,
    run_black_modules: bool | None = None,
    black_config: str | os.PathLike | None = None,
    black_package: str = "black",
    # flake8:
    run_flake8: bool = True,
    flake8_config: str | os.PathLike | None = None,
    flake8_package: str = "flake8",
    # pylint:
    run_pylint: bool = True,
    pylint_rcfile: str | os.PathLike | None = None,
    pylint_modules_rcfile: str | os.PathLike | None = None,
    pylint_package: str = "pylint",
    pylint_ansible_core_package: str | None = "ansible-core",
    pylint_extra_deps: list[str] | None = None,
    # mypy:
    run_mypy: bool = True,
    mypy_config: str | os.PathLike | None = None,
    mypy_package: str = "mypy",
    mypy_ansible_core_package: str | None = "ansible-core",
    mypy_extra_deps: list[str] | None = None,
) -> None:
    """
    Add nox sessions for linting.
    """
    has_formatters = run_isort or run_black or run_black_modules or False
    has_codeqa = run_flake8 or run_pylint
    has_typing = run_mypy

    add_lint(
        has_formatters=has_formatters, has_codeqa=has_codeqa, has_typing=has_typing
    )

    if has_formatters:
        add_formatters(
            run_isort=run_isort,
            isort_config=isort_config,
            isort_package=isort_package,
            run_black=run_black,
            run_black_modules=run_black_modules,
            black_config=black_config,
            black_package=black_package,
        )

    if has_codeqa:
        add_codeqa(
            run_flake8=run_flake8,
            flake8_config=flake8_config,
            flake8_package=flake8_package,
            run_pylint=run_pylint,
            pylint_rcfile=pylint_rcfile,
            pylint_modules_rcfile=pylint_modules_rcfile,
            pylint_package=pylint_package,
            pylint_ansible_core_package=pylint_ansible_core_package,
            pylint_extra_deps=pylint_extra_deps or [],
        )

    if has_typing:
        add_typing(
            run_mypy=run_mypy,
            mypy_config=mypy_config,
            mypy_package=mypy_package,
            mypy_ansible_core_package=mypy_ansible_core_package,
            mypy_extra_deps=mypy_extra_deps or [],
        )


def add_docs_check(
    *,
    antsibull_docs_package: str = "antsibull-docs",
    ansible_core_package: str = "ansible-core",
    validate_collection_refs: t.Literal["self", "dependent", "all"] | None = None,
    extra_collections: list[str] | None = None,
):
    """
    Add docs-check session for linting.
    """

    def compose_dependencies() -> list[str]:
        deps = [antsibull_docs_package, ansible_core_package]
        return deps

    def execute_antsibull_docs(
        session: nox.Session, prepared_collections: CollectionSetup
    ) -> None:
        with session.chdir(prepared_collections.current_path):
            collections_path = f"{prepared_collections.current_place}"
            command = [
                "antsibull-docs",
                "lint-collection-docs",
                "--plugin-docs",
                "--skip-rstcheck",
                ".",
            ]
            if validate_collection_refs:
                command.extend(["--validate-collection-refs", validate_collection_refs])
            session.run(*command, env={"ANSIBLE_COLLECTIONS_PATH": collections_path})

    def docs_check(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        prepared_collections = prepare_collections(
            session, extra_collections=extra_collections
        )
        if not prepared_collections:
            session.warn("Skipping antsibull-docs...")
        if prepared_collections:
            execute_antsibull_docs(session, prepared_collections)

    nox.session(docs_check, name="docs-check", default=True)  # type: ignore


def _run_bare_script(
    session: nox.Session, /, name: str, *, extra_data: dict[str, t.Any] | None = None
) -> None:
    files = list_all_files()
    data = prepare_data_script(
        session,
        base_name=name,
        paths=files,
        extra_data=extra_data,
    )
    session.run(
        sys.executable,
        find_data_directory() / f"{name}.py",
        "--data",
        data,
        external=True,
    )


def add_license_check(
    *,
    run_reuse: bool = True,
    reuse_package: str = "reuse",
    run_license_check: bool = True,
    license_check_extra_ignore_paths: list[str] | None = None,
):
    """
    Add license-check session for license checks.
    """

    def compose_dependencies() -> list[str]:
        deps = []
        if run_reuse:
            deps.append(reuse_package)
        return deps

    def license_check(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        if run_reuse:
            session.run("reuse", "lint")
        if run_license_check:
            _run_bare_script(
                session,
                "license-check",
                extra_data={
                    "extra_ignore_paths": license_check_extra_ignore_paths or [],
                },
            )

    nox.session(license_check, name="license-check", default=True)  # type: ignore


def add_extra_checks(
    *,
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
):
    """
    Add extra-checks session for extra checks.
    """

    def no_unwanted_files(session: nox.Session) -> None:
        _run_bare_script(
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
        )

    def extra_checks(session: nox.Session) -> None:
        if run_no_unwanted_files:
            no_unwanted_files(session)

    nox.session(extra_checks, name="extra-checks", python=False, default=True)  # type: ignore


__all__ = ["add_lint_sessions", "add_docs_check", "add_license_check"]
