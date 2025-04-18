# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Config file schema.
"""

from __future__ import annotations

import os
import typing as t

import pydantic as p

from .ansible import AnsibleCoreVersion
from .utils import Version

try:
    from tomllib import load as _load_toml
except ImportError:
    from tomli import load as _load_toml  # type: ignore


def _parse_version(value: t.Any) -> Version:
    if isinstance(value, Version):
        return value
    if isinstance(value, str) and "." in value:
        return Version.parse(value)
    raise ValueError("Must be version string")


def _parse_ansible_core_version(value: t.Any) -> AnsibleCoreVersion:
    if isinstance(value, Version):
        return value
    if isinstance(value, str):
        if value == "devel":
            return "devel"
        if value == "milestone":
            return "milestone"
        if "." in value:
            return Version.parse(value)
    raise ValueError("Must be ansible-core version string")


PVersion = t.Annotated[Version, p.BeforeValidator(_parse_version)]
PAnsibleCoreVersion = t.Annotated[
    AnsibleCoreVersion, p.BeforeValidator(_parse_ansible_core_version)
]


class _BaseModel(p.BaseModel):
    model_config = p.ConfigDict(frozen=True, extra="allow", validate_default=True)


class SessionLint(_BaseModel):
    """
    Lint session config.
    """

    default: bool = True
    extra_code_files: list[str] = []

    # isort:
    run_isort: bool = True
    isort_config: t.Optional[p.FilePath] = None
    isort_package: str = "isort"

    # black:
    run_black: bool = True
    run_black_modules: t.Optional[bool] = None
    black_config: t.Optional[p.FilePath] = None
    black_package: str = "black"

    # flake8:
    run_flake8: bool = True
    flake8_config: t.Optional[p.FilePath] = None
    flake8_package: str = "flake8"

    # pylint:
    run_pylint: bool = True
    pylint_rcfile: t.Optional[p.FilePath] = None
    pylint_modules_rcfile: t.Optional[p.FilePath] = None
    pylint_package: str = "pylint"
    pylint_ansible_core_package: t.Optional[str] = "ansible-core"
    pylint_extra_deps: list[str] = []

    # yamllint:
    run_yamllint: bool = True
    yamllint_config: t.Optional[p.FilePath] = None
    yamllint_config_plugins: t.Optional[p.FilePath] = None
    yamllint_config_plugins_examples: t.Optional[p.FilePath] = None
    yamllint_package: str = "yamllint"

    # mypy:
    run_mypy: bool = True
    mypy_config: t.Optional[p.FilePath] = None
    mypy_package: str = "mypy"
    mypy_ansible_core_package: t.Optional[str] = "ansible-core"
    mypy_extra_deps: list[str] = []


class SessionDocsCheck(_BaseModel):
    """
    Docs check session config.
    """

    default: bool = True

    antsibull_docs_package: str = "antsibull-docs"
    ansible_core_package: str = "ansible-core"
    validate_collection_refs: t.Optional[t.Literal["self", "dependent", "all"]] = None
    extra_collections: list[str] = []


class SessionLicenseCheck(_BaseModel):
    """
    License check session config.
    """

    default: bool = True

    run_reuse: bool = True
    reuse_package: str = "reuse"
    run_license_check: bool = True
    license_check_extra_ignore_paths: list[str] = []


class ActionGroup(_BaseModel):
    """
    Information about an action group.
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
    exclusions: list[str] = []


class SessionExtraChecks(_BaseModel):
    """
    Extra checks session config.
    """

    default: bool = True

    # no-unwanted-files:
    run_no_unwanted_files: bool = True
    no_unwanted_files_module_extensions: list[str] = [".cs", ".ps1", ".psm1", ".py"]
    no_unwanted_files_other_extensions: list[str] = [".py", ".pyi"]
    no_unwanted_files_yaml_extensions: list[str] = [".yml", ".yaml"]
    no_unwanted_files_skip_paths: list[str] = []
    no_unwanted_files_skip_directories: t.Optional[list[str]] = []
    no_unwanted_files_yaml_directories: t.Optional[list[str]] = [
        "plugins/test/",
        "plugins/filter/",
    ]
    no_unwanted_files_allow_symlinks: bool = False

    # action-groups:
    run_action_groups: bool = False
    action_groups_config: list[ActionGroup] = []


class SessionBuildImportCheck(_BaseModel):
    """
    Collection build and Galaxy import session config.
    """

    default: bool = True

    ansible_core_package: str = "ansible-core"
    run_galaxy_importer: bool = True
    galaxy_importer_package: str = "galaxy-importer"
    # https://github.com/ansible/galaxy-importer#configuration
    galaxy_importer_config_path: t.Optional[p.FilePath] = None


class DevelLikeBranch(_BaseModel):
    """
    A Git repository + branch for a devel-like branch of ansible-core.
    """

    repository: t.Optional[str] = None
    branch: str

    @p.model_validator(mode="before")
    @classmethod
    def _pre_validate(cls, values: t.Any) -> t.Any:
        if isinstance(values, str):
            return {"branch": values}
        if (
            isinstance(values, list)
            and len(values) == 2
            and all(isinstance(v, str) for v in values)
        ):
            return {"repository": values[0], "branch": values[1]}
        return values


class SessionAnsibleTestSanity(_BaseModel):
    """
    Ansible-test sanity tests session config.
    """

    default: bool = False

    include_devel: bool = False
    include_milestone: bool = False
    add_devel_like_branches: list[DevelLikeBranch] = []
    min_version: t.Optional[PVersion] = None
    max_version: t.Optional[PVersion] = None
    except_versions: list[PAnsibleCoreVersion] = []


class SessionAnsibleTestUnits(_BaseModel):
    """
    Ansible-test unit tests session config.
    """

    default: bool = False

    include_devel: bool = False
    include_milestone: bool = False
    add_devel_like_branches: list[DevelLikeBranch] = []
    min_version: t.Optional[PVersion] = None
    max_version: t.Optional[PVersion] = None
    except_versions: list[PAnsibleCoreVersion] = []


class SessionAnsibleTestIntegrationWDefaultContainer(_BaseModel):
    """
    Ansible-test integration tests with default container session config.
    """

    default: bool = False

    include_devel: bool = False
    include_milestone: bool = False
    add_devel_like_branches: list[DevelLikeBranch] = []
    min_version: t.Optional[PVersion] = None
    max_version: t.Optional[PVersion] = None
    except_versions: list[PAnsibleCoreVersion] = []
    core_python_versions: dict[t.Union[PAnsibleCoreVersion, str], list[PVersion]] = {}
    controller_python_versions_only: bool = False

    @p.model_validator(mode="after")
    def _validate_core_keys(self) -> t.Self:
        branch_names = [dlb.branch for dlb in self.add_devel_like_branches]
        for key in self.core_python_versions:
            if isinstance(key, Version) or key in {"devel", "milestone"}:
                continue
            if key in branch_names:
                continue
            raise ValueError(
                f"Unknown ansible-core version or branch name {key!r} in core_python_versions"
            )
        return self


class SessionAnsibleLint(_BaseModel):
    """
    Ansible-lint session config.
    """

    default: bool = True

    ansible_lint_package: str = "ansible-lint"
    strict: bool = False


class Sessions(_BaseModel):
    """
    Configuration of nox sessions to add.
    """

    lint: t.Optional[SessionLint] = None
    docs_check: t.Optional[SessionDocsCheck] = None
    license_check: t.Optional[SessionLicenseCheck] = None
    extra_checks: t.Optional[SessionExtraChecks] = None
    build_import_check: t.Optional[SessionBuildImportCheck] = None
    ansible_test_sanity: t.Optional[SessionAnsibleTestSanity] = None
    ansible_test_units: t.Optional[SessionAnsibleTestUnits] = None
    ansible_test_integration_w_default_container: t.Optional[
        SessionAnsibleTestIntegrationWDefaultContainer
    ] = None
    ansible_lint: t.Optional[SessionAnsibleLint] = None


class CollectionSource(_BaseModel):
    """
    Source from which to install a collection.
    """

    source: str

    @p.model_validator(mode="before")
    @classmethod
    def _pre_validate(cls, values):
        if isinstance(values, str):
            return {"source": values}
        return values


class Config(_BaseModel):
    """
    The contents of a antsibull-nox config file.
    """

    collection_sources: dict[str, CollectionSource] = {}
    sessions: Sessions = Sessions()


def load_config_from_toml(path: str | os.PathLike) -> Config:
    """
    Load a config TOML file.
    """
    with open(path, "rb") as f:
        try:
            data = _load_toml(f)
        except ValueError as exc:
            raise ValueError(f"Error while reading {path}: {exc}") from exc
    return Config.model_validate(data)
