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

from ..paths import (
    filter_paths,
    list_all_files,
)
from .collections import (
    CollectionSetup,
    prepare_collections,
)
from .utils import (
    IN_CI,
    compose_description,
    install,
    run_bare_script,
)

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


def add_formatters(
    *,
    extra_code_files: list[str],
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
        command.extend(filter_paths(CODE_FILES + ["noxfile.py"] + extra_code_files))
        session.run(*command)

    def execute_black_for(session: nox.Session, paths: list[str]) -> None:
        if not paths:
            return
        command = ["black"]
        if run_check:
            command.append("--check")
        if black_config is not None:
            command.extend(["--config", str(black_config)])
        command.extend(session.posargs)
        command.extend(paths)
        session.run(*command)

    def execute_black(session: nox.Session) -> None:
        if run_black and run_black_modules:
            execute_black_for(
                session, filter_paths(CODE_FILES + ["noxfile.py"] + extra_code_files)
            )
            return
        if run_black:
            paths = (
                filter_paths(
                    CODE_FILES,
                    remove=MODULE_PATHS,
                    extensions=[".py"],
                )
                + ["noxfile.py"]
                + extra_code_files
            )
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

    formatters.__doc__ = compose_description(
        prefix={
            "one": "Run code formatter:",
            "other": "Run code formatters:",
        },
        programs={
            "isort": run_isort,
            "black": run_black,
        },
    )
    nox.session(name="formatters", default=False)(formatters)


def add_codeqa(  # noqa: C901
    *,
    extra_code_files: list[str],
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
        command.extend(filter_paths(CODE_FILES + ["noxfile.py"] + extra_code_files))
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
                session,
                install_in_site_packages=False,
                extra_deps_files=["tests/unit/requirements.yml"],
            )
            if not prepared_collections:
                session.warn("Skipping pylint...")
        if run_flake8:
            execute_flake8(session)
        if run_pylint and prepared_collections:
            execute_pylint(session, prepared_collections)

    codeqa.__doc__ = compose_description(
        prefix={
            "other": "Run code QA:",
        },
        programs={
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
    yamllint_package: str,
) -> None:
    """
    Add yamllint session for linting YAML files and plugin/module docs.
    """

    def compose_dependencies() -> list[str]:
        deps = []
        if run_yamllint:
            deps.append(yamllint_package)
        return deps

    def to_str(config: str | os.PathLike | None) -> str | None:
        return str(config) if config else None

    def execute_yamllint(session: nox.Session) -> None:
        # Run yamllint
        all_files = list_all_files()
        cwd = Path.cwd()
        all_yaml_filenames = [
            str(file.relative_to(cwd))
            for file in all_files
            if file.name.lower().endswith((".yml", ".yaml"))
        ]
        if not all_yaml_filenames:
            session.warn("Skipping yamllint since no YAML file was found...")
            return

        command = ["yamllint"]
        if yamllint_config is not None:
            command.extend(
                [
                    "-c",
                    str(yamllint_config),
                ]
            )
        command.append("--strict")
        command.append("--")
        command.extend(all_yaml_filenames)
        command.extend(session.posargs)
        session.run(*command)

    def execute_plugin_yamllint(session: nox.Session) -> None:
        # Run yamllint
        all_files = list_all_files()
        cwd = Path.cwd()
        plugins_dir = cwd / "plugins"
        ignore_dirs = [
            plugins_dir / "action",
            plugins_dir / "module_utils",
            plugins_dir / "plugin_utils",
        ]
        all_plugin_files = [
            file
            for file in all_files
            if file.is_relative_to(plugins_dir)
            and file.name.lower().endswith((".py", ".yml", ".yaml"))
            and not any(file.is_relative_to(dir) for dir in ignore_dirs)
        ]
        if not all_plugin_files:
            session.warn(
                "Skipping yamllint for modules/plugins since"
                " no appropriate Python file was found..."
            )
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
        )

    def yamllint(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        if run_yamllint:
            execute_yamllint(session)
            execute_plugin_yamllint(session)

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
    extra_code_files: list[str],
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
            command.extend(
                prepared_collections.prefix_current_paths(CODE_FILES + extra_code_files)
            )
            session.run(
                *command, env={"MYPYPATH": str(prepared_collections.current_place)}
            )

    def typing(session: nox.Session) -> None:
        install(session, *compose_dependencies())
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
            )

            session.run("antsibull-nox", "lint-config")

    antsibull_nox_config.__doc__ = "Lint antsibull-nox config"
    nox.session(name="antsibull-nox-config", python=False, default=False)(
        antsibull_nox_config
    )


def add_lint_sessions(
    *,
    make_lint_default: bool = True,
    extra_code_files: list[str] | None = None,
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
    # yamllint:
    run_yamllint: bool = False,
    yamllint_config: str | os.PathLike | None = None,
    yamllint_config_plugins: str | os.PathLike | None = None,
    yamllint_config_plugins_examples: str | os.PathLike | None = None,
    yamllint_package: str = "yamllint",
    # mypy:
    run_mypy: bool = True,
    mypy_config: str | os.PathLike | None = None,
    mypy_package: str = "mypy",
    mypy_ansible_core_package: str | None = "ansible-core",
    mypy_extra_deps: list[str] | None = None,
    # antsibull-nox config lint:
    run_antsibullnox_config_lint: bool = True,
) -> None:
    """
    Add nox sessions for linting.
    """
    has_formatters = run_isort or run_black or run_black_modules or False
    has_codeqa = run_flake8 or run_pylint
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
            extra_code_files=extra_code_files or [],
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
            extra_code_files=extra_code_files or [],
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

    if has_yamllint:
        add_yamllint(
            run_yamllint=run_yamllint,
            yamllint_config=yamllint_config,
            yamllint_config_plugins=yamllint_config_plugins,
            yamllint_config_plugins_examples=yamllint_config_plugins_examples,
            yamllint_package=yamllint_package,
        )

    if has_typing:
        add_typing(
            extra_code_files=extra_code_files or [],
            run_mypy=run_mypy,
            mypy_config=mypy_config,
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
