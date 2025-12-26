# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Config file schema.
"""

from __future__ import annotations

import typing as t

import pydantic as p
from antsibull_fileutils.yaml import load_yaml_file
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version as PackagingVersion

from .ansible import MinPythonVersionConstantsWOATC
from .utils import Version


class _BaseModel(p.BaseModel):
    model_config = p.ConfigDict(frozen=True, extra="allow", validate_default=True)


class ModulesConfig(_BaseModel):
    """
    Configuration for modules/module_utils.
    """

    # Python versions supported by modules/module_utils
    python_requires: str = "default"


class AnsibleTestConfig(_BaseModel):
    """
    Ansible-test configuration file.

    See https://github.com/ansible/ansible/blob/devel/test/lib/ansible_test/config/config.yml
    for details on the format.
    """

    modules: ModulesConfig = ModulesConfig()


def load_ansible_test_config(
    *, accept_missing: bool = False, ignore_errors: bool = False
) -> AnsibleTestConfig:
    """
    Load collection's ansible-test config file.
    """
    try:
        data = load_yaml_file("tests/config.yml")
    except FileNotFoundError:
        if accept_missing or ignore_errors:
            return AnsibleTestConfig()
        raise

    try:
        return AnsibleTestConfig.model_validate(data)
    except ValueError:
        if ignore_errors:
            return AnsibleTestConfig()
        raise


def get_min_python_version(
    config: AnsibleTestConfig, *, ignore_errors: bool = False
) -> MinPythonVersionConstantsWOATC | t.Callable[[Version], bool]:
    """
    Given an Ansible-test config file, figures out the minimum Python version
    for modules and module utils.
    """
    if config.modules.python_requires in ("default", "controller"):
        return t.cast(MinPythonVersionConstantsWOATC, config.modules.python_requires)

    try:
        spec_set = SpecifierSet(config.modules.python_requires)
    except InvalidSpecifier:
        if ignore_errors:
            return "default"
        raise

    return lambda version: PackagingVersion(str(version)) in spec_set
