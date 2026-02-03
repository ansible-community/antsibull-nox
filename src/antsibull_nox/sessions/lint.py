# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox lint sessions.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

import nox

from ..collection import (
    load_collection_data_from_disk,
)
from ..messages import Message
from ..messages.parse import (
    parse_mypy_errors,
    parse_pylint_json2_errors,
    parse_ruff_check_errors,
)
from ..paths.match import (
    FileCollector,
)
from ..paths.utils import (
    list_all_files,
    relative_to_walk_up,
)
from .collections import (
    CollectionSetup,
    prepare_collections,
)
from .docs_check import find_extra_docs_rst_files
from .utils import (
    IN_CI,
    compose_description,
    silence_run_verbosity,
)
from .utils.output import (
    print_messages,
)
from .utils.packages import (
    PackageType,
    PackageTypeOrList,
    check_package_types,
    install,
    normalize_package_type,
)
from .utils.paths import (
    PythonDependencies,
    filter_files_cd,
    filter_paths,
)
from .utils.scripts import (
    run_bare_script,
)

CODE_FILES = [
    Path("plugins"),
    Path("tests/unit"),
]

CODE_FILES_W_NOXFILE = [
    Path("plugins"),
    Path("tests/unit"),
    Path("noxfile.py"),
]

MODULE_PATHS = FileCollector.create(
    [
        "plugins/modules/",
        "plugins/module_utils/",
        "tests/unit/plugins/modules/",
        "tests/unit/plugins/module_utils/",
    ],
    glob=False,
)


def _as_list(*args: str | os.PathLike | None) -> list[Path] | None:
    result = [
        (arg if isinstance(arg, Path) else Path(arg)) for arg in args if arg is not None
    ]
    return result or None


def _split_arg(
    session: nox.Session, arg: str | PackageType, arg_name: str, index: int
) -> list[str | PackageType]:
    if not isinstance(arg, str):
        return check_package_types(session, arg_name, [arg])
    args = shlex.split(arg)
    # How to resolve the deprecations:
    #   1. Eventually, make the following warnings errors (in 2.0.0 likely);
    #   2. Eventually, parse str as PackageName as for other
    #      package list arguments (do this in config.py) (in 2.x.0 likely).
    if args != [arg]:
        session.warn(
            f"DEPRECATION WARNING: {arg_name}[{index + 1}] is currently shell-split."
            " This behavior is deprecated and will change in a future release."
            " Specify the dependency as a dictionary with 'type' to avoid ambiguity;"
            " see PackageType in the config file documentation for details."
        )
    for part in args:
        if part.startswith("-"):
            session.warn(
                f"DEPRECATION WARNING: {arg_name}[{index + 1}] contains an argument"
                f" {part!r} starting with a dash."
                " This behavior is deprecated and will stop working in a future release."
                " Specify this dependency as a package type dictionary;"
                " see PackageType in the config file documentation for details."
            )
    return args  # type: ignore


def add_lint(
    *,
    make_lint_default: bool,
    has_formatters: bool,
    has_codeqa: bool,
    has_yamllint: bool,
    has_typing: bool,
    has_config_lint: bool,
) -> None:
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
    if has_yamllint:
        dependent_sessions.append("yamllint")
    if has_typing:
        dependent_sessions.append("typing")
    if has_config_lint:
        dependent_sessions.append("antsibull-nox-config")

    lint.__doc__ = compose_description(
        prefix={
            "one": "Meta session for triggering the following session:",
            "other": "Meta session for triggering the following sessions:",
        },
        programs={
            "formatters": has_formatters,
            "codeqa": has_codeqa,
            "yamllint": has_yamllint,
            "typing": has_typing,
            "antsibull-nox-config": has_config_lint,
        },
    )
    nox.session(
        name="lint",
        default=make_lint_default,
        requires=dependent_sessions,
    )(lint)


def _get_files(
    *,
    code_files: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    split_modules: bool,
    cd_add_python_deps: PythonDependencies = "none",
    config: str | os.PathLike | None,
    config_modules: str | os.PathLike | None,
) -> tuple[list[Path] | None, list[Path] | None, list[Path] | None]:
    files: list[Path] | None = None
    files_modules: list[Path] | None = None
    files_other: list[Path] | None = None
    if split_modules:
        files_modules = filter_paths(
            code_files,
            restrict=module_files,
            extensions=[".py"],
            with_cd=True,
            cd_add_python_deps=cd_add_python_deps,
            paths_to_trigger_full_build=_as_list(config_modules),
        )
        files_other = filter_paths(
            code_files,
            remove=module_files,
            extensions=[".py"],
            with_cd=True,
            cd_add_python_deps=cd_add_python_deps,
            paths_to_trigger_full_build=_as_list(config),
        )
    else:
        files = filter_paths(
            code_files,
            extensions=[".py"],
            with_cd=True,
            cd_add_python_deps=cd_add_python_deps,
            paths_to_trigger_full_build=_as_list(config),
        )
    return files, files_modules, files_other


def _execute_isort_for(
    session: nox.Session,
    *,
    old_cwd: Path,
    root_dir: Path,
    collection_dir: Path,
    run_check: bool,
    paths: list[Path],
    isort_config: str | os.PathLike | None,
    what_for: str = "",
) -> None:
    if not paths:
        session.warn(f"Skipping isort{what_for} (no files to process)")
        return
    command: list[str] = [
        "isort",
        "--src",
        ".",
    ]
    if run_check:
        command.append("--check")
    if isort_config is not None:
        command.extend(
            [
                "--settings-file",
                str(relative_to_walk_up((old_cwd / isort_config).resolve(), root_dir)),
            ]
        )
    command.extend(session.posargs)
    relative_dir = collection_dir.relative_to(root_dir)
    for file in paths:
        command.append(str(relative_dir / file))
    session.run(*command)


def _execute_isort(
    session: nox.Session,
    *,
    root_dir: Path,
    collection_dir: Path,
    run_check: bool,
    code_files: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    isort_config: str | os.PathLike | None,
    isort_modules_config: str | os.PathLike | None,
) -> None:
    files, files_modules, files_other = _get_files(
        code_files=code_files,
        module_files=module_files,
        split_modules=isort_modules_config is not None
        and isort_modules_config != isort_config,
        config=isort_config,
        config_modules=isort_modules_config or isort_config,
    )
    old_cwd = Path.cwd()
    with session.chdir(root_dir):
        if files is not None:
            _execute_isort_for(
                session,
                old_cwd=old_cwd,
                root_dir=root_dir,
                collection_dir=collection_dir,
                run_check=run_check,
                paths=files,
                isort_config=isort_config,
            )
        if files_modules is not None:
            _execute_isort_for(
                session,
                old_cwd=old_cwd,
                root_dir=root_dir,
                collection_dir=collection_dir,
                run_check=run_check,
                paths=files_modules,
                isort_config=isort_modules_config or isort_config,
                what_for=" for modules and module utils",
            )
        if files_other is not None:
            _execute_isort_for(
                session,
                old_cwd=old_cwd,
                root_dir=root_dir,
                collection_dir=collection_dir,
                run_check=run_check,
                paths=files_other,
                isort_config=isort_config,
                what_for=" for other files",
            )


def _execute_black_for(
    session: nox.Session,
    *,
    paths: list[Path],
    run_check: bool,
    black_config: str | os.PathLike | None,
    what_for: str = "",
) -> None:
    if not paths:
        session.warn(f"Skipping black{what_for} (no files to process)")
        return
    command = ["black"]
    if run_check:
        command.append("--check")
    if black_config is not None:
        command.extend(["--config", str(black_config)])
    command.extend(session.posargs)
    command.extend(str(path) for path in paths)
    session.run(*command)


def _execute_black(
    session: nox.Session,
    *,
    run_check: bool,
    code_files: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    run_black: bool,
    run_black_modules: bool | None,
    black_config: str | os.PathLike | None,
    black_modules_config: str | os.PathLike | None,
) -> None:
    if (
        run_black
        and run_black_modules
        and (black_modules_config is None or black_modules_config == black_config)
    ):
        _execute_black_for(
            session,
            paths=filter_paths(
                code_files,
                extensions=[".py"],
                with_cd=True,
                paths_to_trigger_full_build=_as_list(black_config),
            ),
            run_check=run_check,
            black_config=black_config,
        )
        return
    if run_black:
        paths = filter_paths(
            code_files,
            remove=module_files,
            extensions=[".py"],
            with_cd=True,
            paths_to_trigger_full_build=_as_list(black_config),
        )
        _execute_black_for(
            session,
            paths=paths,
            run_check=run_check,
            black_config=black_config,
            what_for=" for other plugins",
        )
    if run_black_modules:
        paths = filter_paths(
            code_files,
            restrict=module_files,
            extensions=[".py"],
            with_cd=True,
            paths_to_trigger_full_build=_as_list(black_modules_config or black_config),
        )
        _execute_black_for(
            session,
            paths=paths,
            run_check=run_check,
            black_config=black_modules_config or black_config,
            what_for=" for modules and module utils",
        )


def _execute_ruff_format_for(
    session: nox.Session,
    *,
    run_check: bool,
    files: list[Path],
    ruff_format_config: str | os.PathLike | None,
    what_for: str = "",
) -> None:
    if not files:
        session.warn(f"Skipping ruff format{what_for} (no files to process)")
        return
    command: list[str] = [
        "ruff",
        "format",
    ]
    if run_check:
        command.append("--check")
    if ruff_format_config is not None:
        command.extend(["--config", str(ruff_format_config)])
    command.extend(session.posargs)
    command.extend(str(file) for file in files)
    session.run(*command)


def _execute_ruff_format(
    session: nox.Session,
    *,
    run_check: bool,
    code_files: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    ruff_format_config: str | os.PathLike | None,
    ruff_format_modules_config: str | os.PathLike | None,
) -> None:
    files, files_modules, files_other = _get_files(
        code_files=code_files,
        module_files=module_files,
        split_modules=ruff_format_modules_config is not None
        and ruff_format_modules_config != ruff_format_config,
        config=ruff_format_config,
        config_modules=ruff_format_modules_config or ruff_format_config,
    )
    if files is not None:
        _execute_ruff_format_for(
            session,
            run_check=run_check,
            files=files,
            ruff_format_config=ruff_format_config,
        )
    if files_modules is not None:
        _execute_ruff_format_for(
            session,
            run_check=run_check,
            files=files_modules,
            ruff_format_config=ruff_format_modules_config or ruff_format_config,
            what_for=" for modules and module utils",
        )
    if files_other is not None:
        _execute_ruff_format_for(
            session,
            run_check=run_check,
            files=files_other,
            ruff_format_config=ruff_format_config,
            what_for=" for other files",
        )


def _execute_ruff_autofix_for(
    session: nox.Session,
    *,
    old_cwd: Path,
    root_dir: Path,
    collection_dir: Path,
    run_check: bool,
    files: list[Path],
    ruff_autofix_config: str | os.PathLike | None,
    ruff_autofix_select: list[str],
    what_for: str = "",
) -> None:
    if not files:
        session.warn(f"Skipping ruff autofix{what_for} (no files to process)")
        return
    command: list[str] = [
        "ruff",
        "check",
    ]
    if not run_check:
        command.append("--fix")
    if ruff_autofix_config is not None:
        command.extend(
            [
                "--config",
                str(
                    relative_to_walk_up(
                        (old_cwd / ruff_autofix_config).resolve(), root_dir
                    )
                ),
            ]
        )
    if ruff_autofix_select:
        command.extend(["--select", ",".join(ruff_autofix_select)])
    command.extend(session.posargs)
    relative_dir = collection_dir.relative_to(root_dir)
    for file in files:
        command.append(str(relative_dir / file))
    session.run(*command)


def _execute_ruff_autofix(
    session: nox.Session,
    *,
    root_dir: Path,
    collection_dir: Path,
    run_check: bool,
    code_files: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    ruff_autofix_config: str | os.PathLike | None,
    ruff_autofix_modules_config: str | os.PathLike | None,
    ruff_autofix_select: list[str],
) -> None:
    files, files_modules, files_other = _get_files(
        code_files=code_files,
        module_files=module_files,
        split_modules=ruff_autofix_modules_config is not None
        and ruff_autofix_modules_config != ruff_autofix_config,
        config=ruff_autofix_config,
        config_modules=ruff_autofix_modules_config or ruff_autofix_config,
    )
    old_cwd = Path.cwd()
    with session.chdir(root_dir):
        if files is not None:
            _execute_ruff_autofix_for(
                session,
                old_cwd=old_cwd,
                root_dir=root_dir,
                collection_dir=collection_dir,
                run_check=run_check,
                files=files,
                ruff_autofix_config=ruff_autofix_config,
                ruff_autofix_select=ruff_autofix_select,
            )
        if files_modules is not None:
            _execute_ruff_autofix_for(
                session,
                old_cwd=old_cwd,
                root_dir=root_dir,
                collection_dir=collection_dir,
                run_check=run_check,
                files=files_modules,
                ruff_autofix_config=ruff_autofix_modules_config or ruff_autofix_config,
                ruff_autofix_select=ruff_autofix_select,
                what_for=" for modules and module utils",
            )
        if files_other is not None:
            _execute_ruff_autofix_for(
                session,
                old_cwd=old_cwd,
                root_dir=root_dir,
                collection_dir=collection_dir,
                run_check=run_check,
                files=files_other,
                ruff_autofix_config=ruff_autofix_config,
                ruff_autofix_select=ruff_autofix_select,
                what_for=" for other files",
            )


def add_formatters(
    *,
    code_files: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    # isort:
    run_isort: bool,
    isort_config: str | os.PathLike | None,
    isort_modules_config: str | os.PathLike | None,
    isort_package: PackageTypeOrList,
    # black:
    run_black: bool,
    run_black_modules: bool | None,
    black_config: str | os.PathLike | None,
    black_modules_config: str | os.PathLike | None,
    black_package: PackageTypeOrList,
    # ruff format:
    run_ruff_format: bool,
    ruff_format_config: str | os.PathLike | None,
    ruff_format_modules_config: str | os.PathLike | None,
    ruff_format_package: PackageTypeOrList,
    # ruff autofix:
    run_ruff_autofix: bool,
    ruff_autofix_config: str | os.PathLike | None,
    ruff_autofix_modules_config: str | os.PathLike | None,
    ruff_autofix_package: PackageTypeOrList,
    ruff_autofix_select: list[str],
) -> None:
    """
    Add nox session for formatters.
    """
    if run_black_modules is None:
        run_black_modules = run_black
    run_check = IN_CI

    def compose_dependencies(session: nox.Session) -> list[PackageType]:
        deps = []
        if run_isort:
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.isort_package",
                    normalize_package_type(isort_package),
                )
            )
        if run_black or run_black_modules:
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.black_package",
                    normalize_package_type(black_package),
                )
            )
        if (
            run_ruff_format
            and run_ruff_autofix
            and ruff_format_package == ruff_autofix_package
        ):
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.ruff_format_package",
                    normalize_package_type(ruff_format_package),
                )
            )
        else:
            if run_ruff_format:
                deps.extend(
                    check_package_types(
                        session,
                        "sessions.lint.ruff_format_package",
                        normalize_package_type(ruff_format_package),
                    )
                )
            if run_ruff_autofix:
                deps.extend(
                    check_package_types(
                        session,
                        "sessions.lint.ruff_autofix_package",
                        normalize_package_type(ruff_autofix_package),
                    )
                )
        return deps

    def formatters(session: nox.Session) -> None:
        install(session, *compose_dependencies(session))
        if run_isort or run_ruff_autofix:
            cwd = Path.cwd()
            cd = load_collection_data_from_disk(cwd)
            root_dir = Path(session.create_tmp()).resolve() / "collection-root"
            namespace_dir = root_dir / "ansible_collections" / cd.namespace
            namespace_dir.mkdir(parents=True, exist_ok=True)
            collection_path = namespace_dir / cd.name
            if not collection_path.exists():
                collection_path.symlink_to(
                    relative_to_walk_up(cwd, namespace_dir),
                    target_is_directory=True,
                )
        if run_isort:
            _execute_isort(
                session,
                root_dir=root_dir,
                collection_dir=collection_path,
                run_check=run_check,
                code_files=code_files,
                module_files=module_files,
                isort_config=isort_config,
                isort_modules_config=isort_modules_config,
            )
        if run_black or run_black_modules:
            _execute_black(
                session,
                run_check=run_check,
                code_files=code_files,
                module_files=module_files,
                run_black=run_black,
                run_black_modules=run_black_modules,
                black_config=black_config,
                black_modules_config=black_modules_config,
            )
        if run_ruff_format:
            _execute_ruff_format(
                session,
                run_check=run_check,
                code_files=code_files,
                module_files=module_files,
                ruff_format_config=ruff_format_config,
                ruff_format_modules_config=ruff_format_modules_config,
            )
        if run_ruff_autofix:
            _execute_ruff_autofix(
                session,
                root_dir=root_dir,
                collection_dir=collection_path,
                run_check=run_check,
                code_files=code_files,
                module_files=module_files,
                ruff_autofix_config=ruff_autofix_config,
                ruff_autofix_modules_config=ruff_autofix_modules_config,
                ruff_autofix_select=ruff_autofix_select,
            )

    formatters.__doc__ = compose_description(
        prefix={
            "one": "Run code formatter:",
            "other": "Run code formatters:",
        },
        programs={
            "isort": run_isort,
            "black": run_black,
            "ruff format": run_ruff_format,
            "ruff check --fix": run_ruff_autofix,
        },
    )
    nox.session(name="formatters", default=False)(formatters)


def add_codeqa(  # noqa: C901
    *,
    code_files: list[Path] | FileCollector,
    code_files_pylint: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    # ruff check:
    run_ruff_check: bool,
    ruff_check_config: str | os.PathLike | None,
    ruff_check_modules_config: str | os.PathLike | None,
    ruff_check_package: PackageTypeOrList,
    # flake8:
    run_flake8: bool,
    flake8_config: str | os.PathLike | None,
    flake8_modules_config: str | os.PathLike | None,
    flake8_package: PackageTypeOrList,
    # pylint:
    run_pylint: bool,
    pylint_rcfile: str | os.PathLike | None,
    pylint_modules_rcfile: str | os.PathLike | None,
    pylint_package: PackageTypeOrList,
    pylint_ansible_core_package: PackageTypeOrList | None,
    pylint_extra_deps: list[str | PackageType],
) -> None:
    """
    Add nox session for codeqa.
    """

    def compose_dependencies(session: nox.Session) -> list[PackageType]:
        deps = []
        if run_ruff_check:
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.ruff_check_package",
                    normalize_package_type(ruff_check_package),
                )
            )
        if run_flake8:
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.flake8_package",
                    normalize_package_type(flake8_package),
                )
            )
        if run_pylint:
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.pylint_package",
                    normalize_package_type(pylint_package),
                )
            )
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.pylint_ansible_core_package",
                    normalize_package_type(pylint_ansible_core_package),
                )
            )
            if os.path.isdir("tests/unit"):
                deps.append("pytest")
                if os.path.isfile("tests/unit/requirements.txt"):
                    deps.extend(["-r", "tests/unit/requirements.txt"])
            for idx, extra_dep in enumerate(pylint_extra_deps):
                deps.extend(
                    _split_arg(
                        session, extra_dep, "sessions.lint.pylint_extra_deps", idx
                    )
                )
        return deps

    def execute_ruff_check_impl(
        session: nox.Session,
        prepared_collections: CollectionSetup,
        *,
        files: list[Path],
        config: str | os.PathLike | None,
        what_for: str = "",
    ) -> list[Message]:
        if not files:
            session.warn(f"Skipping ruff check{what_for} (no files to process)")
            return []
        command: list[str] = [
            "ruff",
            "check",
            # We use --quiet to avoid printing warnings on stderr, see
            # https://github.com/ansible-community/antsibull-nox/issues/184:
            "--quiet",
            "--no-respect-gitignore",
            "--output-format=json",
        ]
        if config is not None:
            command.extend(
                [
                    "--config",
                    os.path.join(prepared_collections.current_collection.path, config),
                ]
            )
        command.extend(session.posargs)
        command.extend(
            str(path) for path in prepared_collections.prefix_current_paths(files)
        )
        # https://docs.astral.sh/ruff/linter/#exit-codes
        output = session.run(*command, silent=True, success_codes=[0, 1])

        return (
            parse_ruff_check_errors(
                source_path=prepared_collections.current_path,
                output=output,
            )
            if output
            else []
        )

    def execute_ruff_check(
        session: nox.Session,
        prepared_collections: CollectionSetup,
    ) -> None:
        files, files_modules, files_other = _get_files(
            code_files=code_files,
            module_files=module_files,
            split_modules=ruff_check_modules_config is not None
            and ruff_check_modules_config != ruff_check_config,
            config=ruff_check_config,
            config_modules=ruff_check_modules_config or ruff_check_config,
        )

        messages = []
        with session.chdir(prepared_collections.current_place), silence_run_verbosity():
            if files is not None:
                messages.extend(
                    execute_ruff_check_impl(
                        session,
                        prepared_collections,
                        files=files,
                        config=ruff_check_config,
                    )
                )
            if files_modules is not None:
                messages.extend(
                    execute_ruff_check_impl(
                        session,
                        prepared_collections,
                        files=files_modules,
                        config=ruff_check_modules_config or ruff_check_config,
                        what_for=" for modules and module utils",
                    )
                )
            if files_other is not None:
                messages.extend(
                    execute_ruff_check_impl(
                        session,
                        prepared_collections,
                        files=files_other,
                        config=ruff_check_config,
                        what_for=" for other files",
                    )
                )

        print_messages(
            session=session,
            messages=messages,
            fail_msg="Ruff check failed",
        )

    def execute_flake8_impl(
        session: nox.Session,
        *,
        files: list[Path],
        config: str | os.PathLike | None,
        what_for: str = "",
    ) -> None:
        if not files:
            session.warn(f"Skipping flake8{what_for} (no files to process)")
            return
        command: list[str] = [
            "flake8",
        ]
        if config is not None:
            command.extend(["--config", str(config)])
        command.extend(session.posargs)
        command.extend(str(file) for file in files)
        session.run(*command)

    def execute_flake8(session: nox.Session) -> None:
        files, files_modules, files_other = _get_files(
            code_files=code_files,
            module_files=module_files,
            split_modules=flake8_modules_config is not None
            and flake8_modules_config != flake8_config,
            config=flake8_config,
            config_modules=flake8_modules_config or flake8_config,
        )
        if files is not None:
            execute_flake8_impl(session, files=files, config=flake8_config)
        if files_modules is not None:
            execute_flake8_impl(
                session,
                files=files_modules,
                config=flake8_modules_config or flake8_config,
                what_for=" for modules and module utils",
            )
        if files_other is not None:
            execute_flake8_impl(
                session,
                files=files_other,
                config=flake8_config,
                what_for=" for other files",
            )

    def execute_pylint_impl(
        session: nox.Session,
        prepared_collections: CollectionSetup,
        config: os.PathLike | str | None,
        paths: list[Path],
        what_for: str = "",
    ) -> list[Message]:
        if not paths:
            session.warn(f"Skipping pylint{what_for} (no files to process)")
            return []
        command = ["pylint"]
        if config is not None:
            command.extend(
                [
                    "--rcfile",
                    os.path.join(prepared_collections.current_collection.path, config),
                ]
            )
        command.extend(["--source-roots", "."])
        command.extend(["--output-format", "json2"])
        command.extend(session.posargs)
        command.extend(
            str(path) for path in prepared_collections.prefix_current_paths(paths)
        )
        with silence_run_verbosity(), silence_run_verbosity():
            # Exit code is OR of some of 1, 2, 4, 8, 16
            output = session.run(
                *command, silent=True, success_codes=list(range(0, 32))
            )

        return (
            parse_pylint_json2_errors(
                source_path=prepared_collections.current_path,
                output=output,
            )
            if output
            else []
        )

    def execute_pylint(
        session: nox.Session, prepared_collections: CollectionSetup
    ) -> None:
        files, files_modules, files_other = _get_files(
            code_files=code_files_pylint,
            module_files=module_files,
            split_modules=pylint_modules_rcfile is not None
            and pylint_modules_rcfile != pylint_rcfile,
            cd_add_python_deps="importing-changed",
            config=pylint_rcfile,
            config_modules=pylint_modules_rcfile or pylint_rcfile,
        )

        messages = []
        with session.chdir(prepared_collections.current_place):
            if files is not None:
                messages.extend(
                    execute_pylint_impl(
                        session,
                        prepared_collections,
                        pylint_modules_rcfile or pylint_rcfile,
                        files,
                    )
                )
            if files_modules is not None:
                messages.extend(
                    execute_pylint_impl(
                        session,
                        prepared_collections,
                        pylint_modules_rcfile or pylint_rcfile,
                        files_modules,
                        what_for=" for modules and module utils",
                    )
                )
            if files_other is not None:
                messages.extend(
                    execute_pylint_impl(
                        session,
                        prepared_collections,
                        pylint_modules_rcfile or pylint_rcfile,
                        files_other,
                        what_for=" for other files",
                    )
                )

        print_messages(session=session, messages=messages, fail_msg="Pylint failed")

    def codeqa(session: nox.Session) -> None:
        install(session, *compose_dependencies(session))
        prepared_collections: CollectionSetup | None = None
        if run_ruff_check or run_pylint:
            prepared_collections = prepare_collections(
                session,
                install_in_site_packages=False,
                extra_deps_files=["tests/unit/requirements.yml"],
            )
            if not prepared_collections:
                session.warn("Skipping pylint...")
        if run_ruff_check and prepared_collections:
            execute_ruff_check(session, prepared_collections)
        if run_flake8:
            execute_flake8(session)
        if run_pylint and prepared_collections:
            execute_pylint(session, prepared_collections)

    codeqa.__doc__ = compose_description(
        prefix={
            "other": "Run code QA:",
        },
        programs={
            "ruff check": run_ruff_check,
            "flake8": run_flake8,
            "pylint": run_pylint,
        },
    )
    nox.session(name="codeqa", default=False)(codeqa)


def add_yamllint(
    *,
    run_yamllint: bool,
    yamllint_config: str | os.PathLike | None,
    yamllint_config_plugins: str | os.PathLike | None,
    yamllint_config_plugins_examples: str | os.PathLike | None,
    yamllint_config_extra_docs: str | os.PathLike | None,
    yamllint_package: PackageTypeOrList,
    yamllint_antsibull_docutils_package: PackageTypeOrList,
) -> None:
    """
    Add yamllint session for linting YAML files and plugin/module docs.
    """

    def compose_dependencies(session: nox.Session) -> list[PackageType]:
        deps = []
        if run_yamllint:
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.yamllint_package",
                    normalize_package_type(yamllint_package),
                )
            )
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.yamllint_antsibull_docutils_package",
                    normalize_package_type(yamllint_antsibull_docutils_package),
                )
            )
        return deps

    def to_str(config: str | os.PathLike | None) -> str | None:
        return str(config) if config else None

    def execute_yamllint(session: nox.Session) -> None:
        all_files = list_all_files()
        all_yaml_filenames = filter_files_cd(
            [
                file
                for file in all_files
                if file.name.lower().endswith((".yml", ".yaml"))
            ],
            paths_to_trigger_full_build=_as_list(yamllint_config),
        )
        if not all_yaml_filenames:
            session.warn("Skipping yamllint (no files to process)")
            return

        run_bare_script(
            session,
            "file-yamllint",
            use_session_python=True,
            files=all_yaml_filenames,
            extra_data={
                "config": to_str(yamllint_config),
            },
            process_messages=True,
        )

    def execute_plugin_yamllint(session: nox.Session) -> None:
        all_files = list_all_files()
        cwd = Path.cwd()
        plugins_dir = cwd / "plugins"
        ignore_dirs = [
            plugins_dir / "action",
            plugins_dir / "module_utils",
            plugins_dir / "plugin_utils",
        ]
        all_plugin_files = filter_files_cd(
            [
                file
                for file in all_files
                if file.is_relative_to(plugins_dir)
                and file.name.lower().endswith((".py", ".yml", ".yaml"))
                and not any(file.is_relative_to(dir) for dir in ignore_dirs)
            ],
            paths_to_trigger_full_build=_as_list(
                yamllint_config_plugins or yamllint_config,
                yamllint_config_plugins_examples,
            ),
        )
        if not all_plugin_files:
            session.warn("Skipping yamllint for modules/plugins (no files to process)")
            return
        run_bare_script(
            session,
            "plugin-yamllint",
            use_session_python=True,
            files=all_plugin_files,
            extra_data={
                "config": to_str(yamllint_config_plugins or yamllint_config),
                "config_examples": to_str(
                    yamllint_config_plugins_examples
                    or yamllint_config_plugins
                    or yamllint_config
                ),
            },
            process_messages=True,
        )

    def execute_extra_docs_yamllint(session: nox.Session) -> None:
        all_extra_docs = filter_files_cd(
            find_extra_docs_rst_files(),
            paths_to_trigger_full_build=_as_list(
                yamllint_config_extra_docs
                or yamllint_config_plugins_examples
                or yamllint_config_plugins
                or yamllint_config
            ),
        )
        if not all_extra_docs:
            session.warn("Skipping yamllint for extra docs (no files to process)")
            return
        run_bare_script(
            session,
            "rst-yamllint",
            use_session_python=True,
            files=all_extra_docs,
            extra_data={
                "config": to_str(
                    yamllint_config_extra_docs
                    or yamllint_config_plugins_examples
                    or yamllint_config_plugins
                    or yamllint_config
                ),
            },
            process_messages=True,
        )

    def yamllint(session: nox.Session) -> None:
        install(session, *compose_dependencies(session))
        if run_yamllint:
            execute_yamllint(session)
            execute_plugin_yamllint(session)
            execute_extra_docs_yamllint(session)

    yamllint.__doc__ = compose_description(
        prefix={
            "one": "Run YAML checker:",
            "other": "Run YAML checkers:",
        },
        programs={
            "yamllint": run_yamllint,
        },
    )
    nox.session(name="yamllint", default=False)(yamllint)


def add_typing(
    *,
    code_files: list[Path] | FileCollector,
    module_files: list[Path] | FileCollector,
    run_mypy: bool,
    mypy_config: str | os.PathLike | None,
    mypy_modules_config: str | os.PathLike | None,
    mypy_package: PackageTypeOrList,
    mypy_ansible_core_package: PackageTypeOrList | None,
    mypy_extra_deps: list[str | PackageType],
) -> None:
    """
    Add nox session for typing.
    """

    def compose_dependencies(session: nox.Session) -> list[PackageType]:
        deps = []
        if run_mypy:
            deps.extend(
                check_package_types(
                    session,
                    "sessions.lint.mypy_package",
                    normalize_package_type(mypy_package),
                )
            )
            if mypy_ansible_core_package is not None:
                deps.extend(
                    check_package_types(
                        session,
                        "sessions.lint.mypy_ansible_core_package",
                        normalize_package_type(mypy_ansible_core_package),
                    )
                )
            if os.path.isdir("tests/unit"):
                deps.append("pytest")
                if os.path.isfile("tests/unit/requirements.txt"):
                    deps.extend(["-r", "tests/unit/requirements.txt"])
            for idx, extra_dep in enumerate(mypy_extra_deps):
                deps.extend(
                    _split_arg(session, extra_dep, "sessions.lint.mypy_extra_deps", idx)
                )
        return deps

    def execute_mypy_impl(
        session: nox.Session,
        prepared_collections: CollectionSetup,
        *,
        files: list[Path],
        config: str | os.PathLike | None,
        what_for: str = "",
    ) -> list[Message]:
        files = prepared_collections.prefix_current_paths(files)
        if not files:
            session.warn(f"Skipping mypy{what_for} (no files to process)")
            return []
        command = ["mypy"]
        if config is not None:
            command.extend(
                [
                    "--config-file",
                    os.path.join(prepared_collections.current_collection.path, config),
                ]
            )
        command.append("--namespace-packages")
        command.append("--explicit-package-bases")
        command.extend(["--output", "json"])
        command.extend(session.posargs)
        command.extend(str(file) for file in files)
        with silence_run_verbosity():
            output = session.run(
                *command,
                env={"MYPYPATH": str(prepared_collections.current_place)},
                silent=True,
                success_codes=(0, 1, 2),
            )

        return (
            parse_mypy_errors(
                root_path=prepared_collections.current_place,
                source_path=prepared_collections.current_path,
                output=output,
            )
            if output
            else []
        )

    def execute_mypy(
        session: nox.Session, prepared_collections: CollectionSetup
    ) -> None:
        files, files_modules, files_other = _get_files(
            code_files=code_files,
            module_files=module_files,
            split_modules=mypy_modules_config is not None
            and mypy_modules_config != mypy_config,
            cd_add_python_deps="importing-changed",
            config=mypy_config,
            config_modules=mypy_modules_config or mypy_config,
        )

        messages = []
        with session.chdir(prepared_collections.current_place):
            if files is not None:
                messages.extend(
                    execute_mypy_impl(
                        session, prepared_collections, files=files, config=mypy_config
                    )
                )
            if files_modules is not None:
                messages.extend(
                    execute_mypy_impl(
                        session,
                        prepared_collections,
                        files=files_modules,
                        config=mypy_modules_config or mypy_config,
                        what_for=" for modules and module utils",
                    )
                )
            if files_other is not None:
                messages.extend(
                    execute_mypy_impl(
                        session,
                        prepared_collections,
                        files=files_other,
                        config=mypy_config,
                        what_for=" for other files",
                    )
                )

        print_messages(
            session=session,
            messages=messages,
            fail_msg="Mypy failed",
        )

    def typing(session: nox.Session) -> None:
        install(session, *compose_dependencies(session))
        prepared_collections = prepare_collections(
            session,
            install_in_site_packages=False,
            extra_deps_files=["tests/unit/requirements.yml"],
        )
        if not prepared_collections:
            session.warn("Skipping mypy...")
        if run_mypy and prepared_collections:
            execute_mypy(session, prepared_collections)

    typing.__doc__ = compose_description(
        prefix={
            "one": "Run type checker:",
            "other": "Run type checkers:",
        },
        programs={
            "mypy": run_mypy,
        },
    )
    nox.session(name="typing", default=False)(typing)


def add_config_lint(
    *,
    run_antsibullnox_config_lint: bool,
):
    """
    Add nox session for antsibull-nox config linting.
    """

    def antsibull_nox_config(session: nox.Session) -> None:
        if run_antsibullnox_config_lint:
            run_bare_script(
                session,
                "antsibull-nox-lint-config",
                process_messages=True,
            )

    antsibull_nox_config.__doc__ = "Lint antsibull-nox config"
    nox.session(name="antsibull-nox-config", python=False, default=False)(
        antsibull_nox_config
    )


def add_lint_sessions(
    *,
    make_lint_default: bool = True,
    code_files: list[Path] | FileCollector | None = None,
    extra_code_files: list[str] | None = None,
    module_files: list[Path] | FileCollector | None = None,
    # isort:
    run_isort: bool = True,
    isort_config: str | os.PathLike | None = None,
    isort_modules_config: str | os.PathLike | None = None,
    isort_package: PackageTypeOrList = "isort",
    # black:
    run_black: bool = True,
    run_black_modules: bool | None = None,
    black_config: str | os.PathLike | None = None,
    black_modules_config: str | os.PathLike | None = None,
    black_package: PackageTypeOrList = "black",
    # ruff format:
    run_ruff_format: bool = False,
    ruff_format_config: str | os.PathLike | None = None,
    ruff_format_modules_config: str | os.PathLike | None = None,
    ruff_format_package: PackageTypeOrList = "ruff",
    # ruff autofix:
    run_ruff_autofix: bool = False,
    ruff_autofix_config: str | os.PathLike | None = None,
    ruff_autofix_modules_config: str | os.PathLike | None = None,
    ruff_autofix_package: PackageTypeOrList = "ruff",
    ruff_autofix_select: list[str] | None = None,
    # ruff check:
    run_ruff_check: bool = False,
    ruff_check_config: str | os.PathLike | None = None,
    ruff_check_modules_config: str | os.PathLike | None = None,
    ruff_check_package: PackageTypeOrList = "ruff",
    # flake8:
    run_flake8: bool = True,
    flake8_config: str | os.PathLike | None = None,
    flake8_modules_config: str | os.PathLike | None = None,
    flake8_package: PackageTypeOrList = "flake8",
    # pylint:
    run_pylint: bool = True,
    pylint_rcfile: str | os.PathLike | None = None,
    pylint_modules_rcfile: str | os.PathLike | None = None,
    pylint_package: PackageTypeOrList = "pylint",
    pylint_ansible_core_package: PackageTypeOrList | None = "ansible-core",
    pylint_extra_deps: list[str | PackageType] | None = None,
    # yamllint:
    run_yamllint: bool = False,
    yamllint_config: str | os.PathLike | None = None,
    yamllint_config_plugins: str | os.PathLike | None = None,
    yamllint_config_plugins_examples: str | os.PathLike | None = None,
    yamllint_config_extra_docs: str | os.PathLike | None = None,
    yamllint_package: PackageTypeOrList = "yamllint",
    yamllint_antsibull_docutils_package: PackageTypeOrList = "antsibull-docutils",
    # mypy:
    run_mypy: bool = True,
    mypy_config: str | os.PathLike | None = None,
    mypy_modules_config: str | os.PathLike | None = None,
    mypy_package: PackageTypeOrList = "mypy",
    mypy_ansible_core_package: PackageTypeOrList | None = "ansible-core",
    mypy_extra_deps: list[str | PackageType] | None = None,
    # antsibull-nox config lint:
    run_antsibullnox_config_lint: bool = True,
) -> None:
    """
    Add nox sessions for linting.
    """
    if code_files is not None:
        if extra_code_files is not None:
            raise ValueError("Cannot specify both code_files and extra_code_files")
        code_files_w_noxfile = code_files
    else:
        extra_code_files_paths = (
            [Path(file) for file in extra_code_files] if extra_code_files else []
        )
        code_files_w_noxfile = CODE_FILES_W_NOXFILE + extra_code_files_paths
        code_files = CODE_FILES + extra_code_files_paths

    if module_files is None:
        module_files = MODULE_PATHS

    has_formatters = (
        run_isort
        or run_black
        or run_black_modules
        or False
        or run_ruff_format
        or run_ruff_autofix
    )
    has_codeqa = run_ruff_check or run_flake8 or run_pylint
    has_yamllint = run_yamllint
    has_typing = run_mypy
    has_config_lint = run_antsibullnox_config_lint

    add_lint(
        has_formatters=has_formatters,
        has_codeqa=has_codeqa,
        has_yamllint=has_yamllint,
        has_typing=has_typing,
        has_config_lint=has_config_lint,
        make_lint_default=make_lint_default,
    )

    if has_formatters:
        add_formatters(
            code_files=code_files_w_noxfile,
            module_files=module_files,
            run_isort=run_isort,
            isort_config=isort_config,
            isort_modules_config=isort_modules_config,
            isort_package=isort_package,
            run_black=run_black,
            run_black_modules=run_black_modules,
            black_config=black_config,
            black_modules_config=black_modules_config,
            black_package=black_package,
            run_ruff_format=run_ruff_format,
            ruff_format_config=ruff_format_config,
            ruff_format_modules_config=ruff_format_modules_config,
            ruff_format_package=ruff_format_package,
            run_ruff_autofix=run_ruff_autofix,
            ruff_autofix_config=ruff_autofix_config,
            ruff_autofix_modules_config=ruff_autofix_modules_config,
            ruff_autofix_package=ruff_autofix_package,
            ruff_autofix_select=ruff_autofix_select or [],
        )

    if has_codeqa:
        add_codeqa(
            code_files=code_files_w_noxfile,
            code_files_pylint=code_files,
            module_files=module_files,
            run_ruff_check=run_ruff_check,
            ruff_check_config=ruff_check_config,
            ruff_check_modules_config=ruff_check_modules_config,
            ruff_check_package=ruff_check_package,
            run_flake8=run_flake8,
            flake8_config=flake8_config,
            flake8_modules_config=flake8_modules_config,
            flake8_package=flake8_package,
            run_pylint=run_pylint,
            pylint_rcfile=pylint_rcfile,
            pylint_modules_rcfile=pylint_modules_rcfile,
            pylint_package=pylint_package,
            pylint_ansible_core_package=pylint_ansible_core_package,
            pylint_extra_deps=pylint_extra_deps or [],
        )

    if has_yamllint:
        add_yamllint(
            run_yamllint=run_yamllint,
            yamllint_config=yamllint_config,
            yamllint_config_plugins=yamllint_config_plugins,
            yamllint_config_plugins_examples=yamllint_config_plugins_examples,
            yamllint_config_extra_docs=yamllint_config_extra_docs,
            yamllint_package=yamllint_package,
            yamllint_antsibull_docutils_package=yamllint_antsibull_docutils_package,
        )

    if has_typing:
        add_typing(
            code_files=code_files,
            module_files=module_files,
            run_mypy=run_mypy,
            mypy_config=mypy_config,
            mypy_modules_config=mypy_modules_config,
            mypy_package=mypy_package,
            mypy_ansible_core_package=mypy_ansible_core_package,
            mypy_extra_deps=mypy_extra_deps or [],
        )

    if has_config_lint:
        add_config_lint(
            run_antsibullnox_config_lint=run_antsibullnox_config_lint,
        )


__all__ = [
    "add_lint_sessions",
]
