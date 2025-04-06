# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Create nox sessions.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import typing as t
from dataclasses import asdict, dataclass
from pathlib import Path

import nox

from .ansible import (
    AnsibleCoreVersion,
    get_ansible_core_info,
    get_ansible_core_package_name,
    get_supported_core_versions,
)
from .collection import (
    CollectionData,
    force_collection_version,
    load_collection_data_from_disk,
    setup_collections,
    setup_current_tree,
)
from .data_util import prepare_data_script
from .paths import (
    copy_collection,
    copy_directory_tree_into,
    create_temp_directory,
    filter_paths,
    find_data_directory,
    list_all_files,
    remove_path,
)
from .python import get_installed_python_versions
from .utils import Version

# https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables#default-environment-variables
# https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
# https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
IN_CI = os.environ.get("CI") == "true"
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

_SESSIONS: dict[str, list[dict[str, t.Any]]] = {}


def _register(name: str, data: dict[str, t.Any]) -> None:
    if name not in _SESSIONS:
        _SESSIONS[name] = []
    _SESSIONS[name].append(data)


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
    install_in_site_packages: bool,
    extra_deps_files: list[str | os.PathLike] | None = None,
    extra_collections: list[str] | None = None,
    install_out_of_tree: bool = False,  # can not be used with install_in_site_packages=True
) -> CollectionSetup | None:
    """
    Install collections in site-packages.
    """
    if install_out_of_tree and install_in_site_packages:
        raise ValueError(
            "install_out_of_tree=True cannot be combined with install_in_site_packages=True"
        )
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn("No venv. Skip preparing collections...")
        return None
    if install_in_site_packages:
        purelib = (
            session.run(
                "python",
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
                silent=True,
            )
            or ""
        ).strip()
        if not purelib:
            session.warn(
                "Cannot find site-packages (probably due to install-only run)."
                " Skip preparing collections..."
            )
            return None
        place = Path(purelib)
    elif install_out_of_tree:
        place = create_temp_directory(f"antsibull-nox-{session.name}-collection-root-")
    else:
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


def _compose_description(
    *,
    prefix: str | dict[t.Literal["one", "other"], str] | None = None,
    programs: dict[str, str | bool | None],
) -> str:
    parts: list[str] = []

    def add(text: str, *, comma: bool = False) -> None:
        if parts:
            if comma:
                parts.append(", ")
            else:
                parts.append(" ")
        parts.append(text)

    active_programs = [
        (program, value if isinstance(value, str) else None)
        for program, value in programs.items()
        if value not in (False, None)
    ]

    if prefix:
        if isinstance(prefix, dict):
            if len(active_programs) == 1 and "one" in prefix:
                add(prefix["one"])
            else:
                add(prefix["other"])
        else:
            add(prefix)

    for index, (program, value) in enumerate(active_programs):
        if index + 1 == len(active_programs) and index > 0:
            add("and", comma=index > 1)
        add(program, comma=index > 0 and index + 1 < len(active_programs))
        if value is not None:
            add(f"({value})")

    return "".join(parts)


def add_lint(
    *, make_lint_default: bool, has_formatters: bool, has_codeqa: bool, has_typing: bool
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
    if has_typing:
        dependent_sessions.append("typing")

    lint.__doc__ = _compose_description(
        prefix={
            "one": "Meta session for triggering the following session:",
            "other": "Meta session for triggering the following sessions:",
        },
        programs={
            "formatters": has_formatters,
            "codeqa": has_codeqa,
            "typing": has_typing,
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

    formatters.__doc__ = _compose_description(
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

    codeqa.__doc__ = _compose_description(
        prefix={
            "other": "Run code QA:",
        },
        programs={
            "flake8": run_flake8,
            "pylint": run_pylint,
        },
    )
    nox.session(name="codeqa", default=False)(codeqa)


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

    typing.__doc__ = _compose_description(
        prefix={
            "one": "Run type checker:",
            "other": "Run type checkers:",
        },
        programs={
            "mypy": run_mypy,
        },
    )
    nox.session(name="typing", default=False)(typing)


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
        has_formatters=has_formatters,
        has_codeqa=has_codeqa,
        has_typing=has_typing,
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

    if has_typing:
        add_typing(
            extra_code_files=extra_code_files or [],
            run_mypy=run_mypy,
            mypy_config=mypy_config,
            mypy_package=mypy_package,
            mypy_ansible_core_package=mypy_ansible_core_package,
            mypy_extra_deps=mypy_extra_deps or [],
        )


def add_docs_check(
    *,
    make_docs_check_default: bool = True,
    antsibull_docs_package: str = "antsibull-docs",
    ansible_core_package: str = "ansible-core",
    validate_collection_refs: t.Literal["self", "dependent", "all"] | None = None,
    extra_collections: list[str] | None = None,
) -> None:
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
            session,
            install_in_site_packages=False,
            extra_collections=extra_collections,
            install_out_of_tree=True,
        )
        if not prepared_collections:
            session.warn("Skipping antsibull-docs...")
        if prepared_collections:
            execute_antsibull_docs(session, prepared_collections)

    docs_check.__doc__ = "Run 'antsibull-docs lint-collection-docs'"
    nox.session(
        name="docs-check",
        default=make_docs_check_default,
    )(docs_check)


def add_license_check(
    *,
    make_license_check_default: bool = True,
    run_reuse: bool = True,
    reuse_package: str = "reuse",
    run_license_check: bool = True,
    license_check_extra_ignore_paths: list[str] | None = None,
) -> None:
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

    license_check.__doc__ = _compose_description(
        prefix={
            "one": "Run license checker:",
            "other": "Run license checkers:",
        },
        programs={
            "reuse": run_reuse,
            "license-check": (
                "ensure GPLv3+ for plugins" if run_license_check else False
            ),
        },
    )
    nox.session(
        name="license-check",
        default=make_license_check_default,
    )(license_check)


@dataclass
class ActionGroup:
    """
    Defines an action group.
    """

    # Name of the action group.
    name: str
    # Regex pattern to match modules that could belong to this action group.
    pattern: str
    # Doc fragment that members of the action group must have, but no other module
    # must have
    doc_fragment: str
    # Exclusion list of modules that match the regex, but should not be part of the
    # action group. All other modules matching the regex are assumed to be part of
    # the action group.
    exclusions: list[str] | None = None


def add_extra_checks(
    *,
    make_extra_checks_default: bool = True,
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
    # action-groups:
    run_action_groups: bool = False,
    action_groups_config: list[ActionGroup] | None = None,
) -> None:
    """
    Add extra-checks session for extra checks.
    """

    def execute_no_unwanted_files(session: nox.Session) -> None:
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

    def execute_action_groups(session: nox.Session) -> None:
        if action_groups_config is None:
            session.warn("Skipping action-groups since config is not provided...")
            return
        _run_bare_script(
            session,
            "action-groups",
            extra_data={
                "config": [asdict(cfg) for cfg in action_groups_config],
            },
        )

    def extra_checks(session: nox.Session) -> None:
        if run_no_unwanted_files:
            execute_no_unwanted_files(session)
        if run_action_groups:
            execute_action_groups(session)

    extra_checks.__doc__ = _compose_description(
        prefix={
            "one": "Run extra checker:",
            "other": "Run extra checkers:",
        },
        programs={
            "no-unwanted-files": (
                "checks for unwanted files in plugins/"
                if run_no_unwanted_files
                else False
            ),
            "action-groups": "validate action groups" if run_action_groups else False,
        },
    )
    nox.session(
        name="extra-checks",
        python=False,
        default=make_extra_checks_default,
    )(extra_checks)


def add_build_import_check(
    *,
    make_build_import_check_default: bool = True,
    ansible_core_package: str = "ansible-core",
    run_galaxy_importer: bool = True,
    galaxy_importer_package: str = "galaxy-importer",
    galaxy_importer_config_path: (
        str | None
    ) = None,  # https://github.com/ansible/galaxy-importer#configuration
) -> None:
    """
    Add license-check session for license checks.
    """

    def compose_dependencies() -> list[str]:
        deps = [ansible_core_package]
        if run_galaxy_importer:
            deps.append(galaxy_importer_package)
        return deps

    def build_import_check(session: nox.Session) -> None:
        install(session, *compose_dependencies())

        tmp = Path(session.create_tmp())
        collection_dir = tmp / "collection"
        remove_path(collection_dir)
        copy_collection(Path.cwd(), collection_dir)

        collection = load_collection_data_from_disk(
            collection_dir, accept_manifest=False
        )
        version = collection.version
        if not version:
            version = "0.0.1"
            force_collection_version(collection_dir, version=version)

        with session.chdir(collection_dir):
            build_ran = session.run("ansible-galaxy", "collection", "build") is not None

        tarball = (
            collection_dir
            / f"{collection.namespace}-{collection.name}-{version}.tar.gz"
        )
        if build_ran and not tarball.is_file():
            files = "\n".join(
                f"* {path.name}"
                for path in collection_dir.iterdir()
                if not path.is_dir()
            )
            session.error(f"Cannot find file {tarball}! List of all files:\n{files}")

        if run_galaxy_importer and tarball.is_file():
            env = {}
            if galaxy_importer_config_path:
                env["GALAXY_IMPORTER_CONFIG"] = str(
                    Path.cwd() / galaxy_importer_config_path
                )
            with session.chdir(collection_dir):
                import_log = (
                    session.run(
                        "python",
                        "-m",
                        "galaxy_importer.main",
                        tarball.name,
                        env=env,
                        silent=True,
                    )
                    or ""
                )
            if import_log:
                print(import_log)
                error_prefix = "ERROR:"
                errors = []
                for line in import_log.splitlines():
                    if line.startswith(error_prefix):
                        errors.append(line[len(error_prefix) :].strip())
                if errors:
                    messages = "\n".join(f"* {error}" for error in errors)
                    session.warn(
                        "Galaxy importer emitted the following non-fatal"
                        f" error{'' if len(errors) == 1 else 's'}:\n{messages}"
                    )

    build_import_check.__doc__ = _compose_description(
        prefix={
            "one": "Run build and import checker:",
            "other": "Run build and import checkers:",
        },
        programs={
            "build-collection": True,
            "galaxy-importer": (
                "test whether Galaxy will import built collection"
                if run_galaxy_importer
                else False
            ),
        },
    )
    nox.session(
        name="build-import-check",
        default=make_build_import_check_default,
    )(build_import_check)


def _parse_ansible_core_version(
    version: str | AnsibleCoreVersion,
) -> AnsibleCoreVersion:
    if version in ("devel", "milestone"):
        # For some reason mypy doesn't notice that
        return t.cast(AnsibleCoreVersion, version)
    if isinstance(version, Version):
        return version
    return Version.parse(version)


def add_ansible_test_session(
    *,
    name: str,
    description: str | None,
    extra_deps_files: list[str | os.PathLike] | None = None,
    ansible_test_params: list[str],
    add_posargs: bool = True,
    default: bool,
    ansible_core_version: str | AnsibleCoreVersion,
    ansible_core_source: t.Literal["git", "pypi"] = "git",
    ansible_core_branch_name: str | None = None,
    handle_coverage: t.Literal["never", "always", "auto"] = "auto",
    register_name: str | None = None,
    register_extra_data: dict[str, t.Any] | None = None,
) -> None:
    """
    Add generic ansible-test session.

    Returns a list of Python versions set for this session.
    """
    parsed_ansible_core_version = _parse_ansible_core_version(ansible_core_version)

    def compose_dependencies() -> list[str]:
        deps = [
            get_ansible_core_package_name(
                parsed_ansible_core_version,
                source=ansible_core_source,
                branch_name=ansible_core_branch_name,
            )
        ]
        return deps

    def run_ansible_test(session: nox.Session) -> None:
        install(session, *compose_dependencies())
        prepared_collections = prepare_collections(
            session,
            install_in_site_packages=False,
            extra_deps_files=extra_deps_files,
            install_out_of_tree=True,
        )
        if not prepared_collections:
            session.warn("Skipping ansible-test...")
            return
        cwd = Path.cwd()
        with session.chdir(prepared_collections.current_path):
            command = ["ansible-test"] + ansible_test_params
            if add_posargs and session.posargs:
                command.extend(session.posargs)
            session.run(*command)

            coverage = (handle_coverage == "auto" and "--coverage" in command) or (
                handle_coverage == "always"
            )
            if coverage:
                session.run(
                    "ansible-test",
                    "coverage",
                    "xml",
                    "--color",
                    "-v",
                    "--requirements",
                    "--group-by",
                    "command",
                    "--group-by",
                    "version",
                )

            copy_directory_tree_into(
                prepared_collections.current_path / "tests" / "output",
                cwd / "tests" / "output",
            )

    # Determine Python version(s)
    core_info = get_ansible_core_info(parsed_ansible_core_version)
    all_versions = get_installed_python_versions()

    installed_versions = [
        version
        for version in core_info.controller_python_versions
        if version in all_versions
    ]
    python = max(installed_versions or core_info.controller_python_versions)
    python_versions = [python]

    run_ansible_test.__doc__ = description
    nox.session(
        name=name,
        default=default,
        python=[str(python_version) for python_version in python_versions],
    )(run_ansible_test)

    if register_name:
        data = {
            "name": name,
            "ansible-core": str(parsed_ansible_core_version),
            "python": " ".join(str(python) for python in python_versions),
        }
        if register_extra_data:
            data.update(register_extra_data)
        _register(register_name, data)


def add_ansible_test_sanity_test_session(
    *,
    name: str,
    description: str | None,
    default: bool,
    ansible_core_version: str | AnsibleCoreVersion,
    ansible_core_source: t.Literal["git", "pypi"] = "git",
    ansible_core_branch_name: str | None = None,
) -> None:
    """
    Add generic ansible-test sanity test session.
    """
    add_ansible_test_session(
        name=name,
        description=description,
        ansible_test_params=["sanity", "--docker", "-v", "--color"],
        default=default,
        ansible_core_version=ansible_core_version,
        ansible_core_source=ansible_core_source,
        ansible_core_branch_name=ansible_core_branch_name,
        register_name="sanity",
    )


def add_all_ansible_test_sanity_test_sessions(
    *,
    default: bool = False,
    include_devel: bool = False,
    include_milestone: bool = False,
) -> None:
    """
    Add ansible-test sanity test meta session that runs ansible-test sanity
    for all supported ansible-core versions.
    """

    sanity_sessions = []
    for ansible_core_version in get_supported_core_versions(
        include_devel=include_devel, include_milestone=include_milestone
    ):
        name = f"ansible-test-sanity-{ansible_core_version}"
        add_ansible_test_sanity_test_session(
            name=name,
            description=f"Run sanity tests from ansible-core {ansible_core_version}'s ansible-test",
            ansible_core_version=ansible_core_version,
            default=False,
        )
        sanity_sessions.append(name)

    def run_all_sanity_tests(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        pass

    run_all_sanity_tests.__doc__ = (
        "Meta session for running all ansible-test-sanity-* sessions."
    )
    nox.session(
        name="ansible-test-sanity",
        default=default,
        requires=sanity_sessions,
    )(run_all_sanity_tests)


def add_ansible_test_unit_test_session(
    *,
    name: str,
    description: str | None,
    default: bool,
    ansible_core_version: str | AnsibleCoreVersion,
    ansible_core_source: t.Literal["git", "pypi"] = "git",
    ansible_core_branch_name: str | None = None,
) -> None:
    """
    Add generic ansible-test unit test session.
    """
    add_ansible_test_session(
        name=name,
        description=description,
        ansible_test_params=["units", "--docker", "-v", "--color"],
        extra_deps_files=["tests/unit/requirements.yml"],
        default=default,
        ansible_core_version=ansible_core_version,
        ansible_core_source=ansible_core_source,
        ansible_core_branch_name=ansible_core_branch_name,
        register_name="units",
    )


def add_all_ansible_test_unit_test_sessions(
    *,
    default: bool = False,
    include_devel: bool = False,
    include_milestone: bool = False,
) -> None:
    """
    Add ansible-test unit test meta session that runs ansible-test units
    for all supported ansible-core versions.
    """

    units_sessions = []
    for ansible_core_version in get_supported_core_versions(
        include_devel=include_devel, include_milestone=include_milestone
    ):
        name = f"ansible-test-units-{ansible_core_version}"
        add_ansible_test_unit_test_session(
            name=name,
            description=f"Run unit tests with ansible-core {ansible_core_version}'s ansible-test",
            ansible_core_version=ansible_core_version,
            default=False,
        )
        units_sessions.append(name)

    def run_all_unit_tests(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        pass

    run_all_unit_tests.__doc__ = (
        "Meta session for running all ansible-test-units-* sessions."
    )
    nox.session(
        name="ansible-test-units",
        default=default,
        requires=units_sessions,
    )(run_all_unit_tests)


def add_ansible_test_integration_sessions_default_container(
    *,
    include_devel: bool = False,
    include_milestone: bool = False,
    core_python_versions: (
        dict[str | AnsibleCoreVersion, list[str | Version]] | None
    ) = None,
    controller_python_versions_only: bool = False,
    default: bool = False,
) -> None:
    """
    Add ansible-test integration tests using the default Docker container.

    ``core_python_versions`` can be used to restrict the Python versions
    to be used for a specific ansible-core version.

    ``controller_python_versions_only`` can be used to only run against
    controller Python versions.
    """

    def add_integration_tests(ansible_core_version: AnsibleCoreVersion) -> list[str]:
        # Determine Python versions to run tests for
        py_versions = (
            core_python_versions.get(ansible_core_version)
            or core_python_versions.get(str(ansible_core_version))
            if core_python_versions
            else None
        )
        if py_versions is None:
            core_info = get_ansible_core_info(ansible_core_version)
            py_versions = list(
                core_info.controller_python_versions
                if controller_python_versions_only
                else core_info.remote_python_versions
            )

        # Add sessions
        integration_sessions_core: list[str] = []
        for py_version in py_versions:
            name = f"ansible-test-integration-{ansible_core_version}-{py_version}"
            add_ansible_test_session(
                name=name,
                description=(
                    f"Run integration tests from ansible-core {ansible_core_version}'s"
                    f" ansible-test with Python {py_version}"
                ),
                ansible_test_params=[
                    "integration",
                    "--docker",
                    "default",
                    "-v",
                    "--color",
                    "--python",
                    str(py_version),
                ],
                extra_deps_files=["tests/integration/requirements.yml"],
                ansible_core_version=ansible_core_version,
                default=False,
                register_name="integration",
                register_extra_data={
                    "test-container": "default",
                    "test-python": str(py_version),
                },
            )
            integration_sessions_core.append(name)
        return integration_sessions_core

    integration_sessions: list[str] = []
    for ansible_core_version in get_supported_core_versions(
        include_devel=include_devel, include_milestone=include_milestone
    ):
        integration_sessions_core = add_integration_tests(ansible_core_version)
        if integration_sessions_core:
            name = f"ansible-test-integration-{ansible_core_version}"
            integration_sessions.append(name)

            def run_integration_tests(
                session: nox.Session,  # pylint: disable=unused-argument
            ) -> None:
                pass

            run_integration_tests.__doc__ = (
                "Meta session for running all"
                f" ansible-test-integration-{ansible_core_version}-* sessions."
            )
            nox.session(
                name=name,
                requires=integration_sessions_core,
                default=False,
            )(run_integration_tests)

    def ansible_test_integration(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        pass

    ansible_test_integration.__doc__ = (
        "Meta session for running all ansible-test-integration-* sessions."
    )
    nox.session(  # type: ignore
        name="ansible-test-integration",
        requires=integration_sessions,
        default=default,
    )(ansible_test_integration)


def add_matrix_generator() -> None:
    """
    Add a session that generates matrixes for CI systems.
    """

    def matrix_generator(
        session: nox.Session,  # pylint: disable=unused-argument
    ) -> None:
        json_output = os.environ.get("ANTSIBULL_NOX_MATRIX_JSON")
        if json_output:
            print(f"Writing JSON output to {json_output}...")
            with open(json_output, "wt", encoding="utf-8") as f:
                f.write(json.dumps(_SESSIONS))

        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            print(f"Writing GitHub output to {github_output}...")
            with open(github_output, "at", encoding="utf-8") as f:
                for name, sessions in _SESSIONS.items():
                    f.write(f"{name}={json.dumps(sessions)}\n")

        for name, sessions in sorted(_SESSIONS.items()):
            print(f"{name} ({len(sessions)}):")
            for session_data in sessions:
                data = session_data.copy()
                session_name = data.pop("name")
                print(f"  {session_name}: {data}")

    matrix_generator.__doc__ = "Generate matrix for CI systems."
    nox.session(
        name="matrix-generator",
        python=False,
        default=False,
    )(matrix_generator)


__all__ = [
    "ActionGroup",
    "add_build_import_check",
    "add_docs_check",
    "add_extra_checks",
    "add_license_check",
    "add_lint_sessions",
    "add_ansible_test_session",
    "add_ansible_test_sanity_test_session",
    "add_all_ansible_test_sanity_test_sessions",
    "add_ansible_test_unit_test_session",
    "add_all_ansible_test_unit_test_sessions",
    "add_ansible_test_integration_sessions_default_container",
    "add_matrix_generator",
    "install",
    "prepare_collections",
]
