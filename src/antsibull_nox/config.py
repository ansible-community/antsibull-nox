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


class BaseModel(p.BaseModel):
    model_config = p.ConfigDict(frozen=True, extra="allow", validate_default=True)


class SessionLint(BaseModel):
    default: bool = True
    extra_code_files: t.Optional[list[str]] = None

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
    pylint_extra_deps: t.Optional[list[str]] = None

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
    mypy_extra_deps: t.Optional[list[str]] = None


class SessionDocsCheck(BaseModel):
    default: bool = True

    antsibull_docs_package: str = "antsibull-docs"
    ansible_core_package: str = "ansible-core"
    validate_collection_refs: t.Optional[t.Literal["self", "dependent", "all"]] = None
    extra_collections: t.Optional[list[str]] = None


class SessionLicenseCheck(BaseModel):
    default: bool = True

    run_reuse: bool = True
    reuse_package: str = "reuse"
    run_license_check: bool = True
    license_check_extra_ignore_paths: t.Optional[list[str]] = None


class ActionGroup(BaseModel):
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
    exclusions: t.Optional[list[str]] = None


class SessionExtraChecks(BaseModel):
    default: bool = True

    # no-unwanted-files:
    run_no_unwanted_files: bool = True
    no_unwanted_files_module_extensions: t.Optional[list[str]] = (
        None  # default: .cs, .ps1, .psm1, .py
    )
    no_unwanted_files_other_extensions: t.Optional[list[str]] = (
        None  # default: .py, .pyi
    )
    no_unwanted_files_yaml_extensions: t.Optional[list[str]] = (
        None  # default: .yml, .yaml
    )
    no_unwanted_files_skip_paths: t.Optional[list[str]] = None  # default: []
    no_unwanted_files_skip_directories: t.Optional[list[str]] = None  # default: []
    no_unwanted_files_yaml_directories: t.Optional[list[str]] = (
        None  # default: plugins/test/, plugins/filter/
    )
    no_unwanted_files_allow_symlinks: bool = False

    # action-groups:
    run_action_groups: bool = False
    action_groups_config: t.Optional[list[ActionGroup]] = None


class SessionBuildImportCheck(BaseModel):
    default: bool = True

    ansible_core_package: str = "ansible-core"
    run_galaxy_importer: bool = True
    galaxy_importer_package: str = "galaxy-importer"
    # https://github.com/ansible/galaxy-importer#configuration
    galaxy_importer_config_path: t.Optional[p.FilePath] = None


class DevelLikeBranch(BaseModel):
    repository: t.Optional[str] = None
    branch: str

    @p.model_validator(mode="before")
    @classmethod
    def pre_validate(cls, values):
        if isinstance(values, str):
            return {"branch": values}
        if (
            isinstance(values, list)
            and len(values) == 2
            and all(isinstance(v, str) for v in values)
        ):
            return {"repository": values[0], "branch": values[1]}
        return values


class SessionAnsibleTestSanity(BaseModel):
    default: bool = False

    include_devel: bool = False
    include_milestone: bool = False
    add_devel_like_branches: t.Optional[list[DevelLikeBranch]] = None
    min_version: t.Optional[PVersion] = None
    max_version: t.Optional[PVersion] = None
    except_versions: t.Optional[list[PAnsibleCoreVersion]] = None


class SessionAnsibleTestUnits(BaseModel):
    default: bool = False

    include_devel: bool = False
    include_milestone: bool = False
    add_devel_like_branches: t.Optional[list[DevelLikeBranch]] = None
    min_version: t.Optional[PVersion] = None
    max_version: t.Optional[PVersion] = None
    except_versions: t.Optional[list[PAnsibleCoreVersion]] = None


class SessionAnsibleTestIntegrationWDefaultContainer(BaseModel):
    default: bool = False

    include_devel: bool = False
    include_milestone: bool = False
    add_devel_like_branches: t.Optional[list[DevelLikeBranch]] = None
    min_version: t.Optional[PVersion] = None
    max_version: t.Optional[PVersion] = None
    except_versions: t.Optional[list[PAnsibleCoreVersion]] = None
    core_python_versions: t.Optional[dict[PAnsibleCoreVersion, list[PVersion]]] = None
    controller_python_versions_only: bool = False


class SessionAnsibleLint(BaseModel):
    default: bool = True

    ansible_lint_package: str = "ansible-lint"
    strict: bool = False


class Sessions(BaseModel):
    lint: t.Optional[SessionLint] = None
    docs_check: t.Optional[SessionDocsCheck] = None
    license_check: t.Optional[SessionLicenseCheck] = None
    extra_checks: t.Optional[SessionExtraChecks] = None
    import_check: t.Optional[SessionBuildImportCheck] = None
    ansible_test_sanity: t.Optional[SessionAnsibleTestSanity] = None
    ansible_test_units: t.Optional[SessionAnsibleTestUnits] = None
    ansible_test_integration_w_default_container: t.Optional[
        SessionAnsibleTestIntegrationWDefaultContainer
    ] = None
    ansible_lint: t.Optional[SessionAnsibleLint] = None


class CollectionSource(BaseModel):
    source: str

    @p.model_validator(mode="before")
    @classmethod
    def pre_validate(cls, values):
        if isinstance(values, str):
            return {"source": values}
        return values


class Config(BaseModel):
    collection_sources: t.Optional[dict[str, CollectionSource]] = None
    sessions: Sessions = Sessions()


def load_config_from_toml(path: str | os.PathLike) -> Config:
    with open(path, "rb") as f:
        try:
            data = _load_toml(f)
        except ValueError as exc:
            raise ValueError(f"Error while reading {path}: {exc}") from exc
    return Config.model_validate(data)
