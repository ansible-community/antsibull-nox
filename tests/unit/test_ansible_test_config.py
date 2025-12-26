# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

from __future__ import annotations

import re
from pathlib import Path

import pytest
from antsibull_fileutils.yaml import store_yaml_file

from antsibull_nox.ansible_test_config import (
    AnsibleTestConfig,
    ModulesConfig,
    get_min_python_version,
    load_ansible_test_config,
)
from antsibull_nox.utils import Version

from .utils import chdir


def test_load_ansible_test_config(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    config_yml = tests / "config.yml"
    with chdir(tmp_path):
        with pytest.raises(FileNotFoundError):
            load_ansible_test_config()

        config = load_ansible_test_config(accept_missing=True)
        assert config.modules.python_requires == "default"
        assert config.modules == ModulesConfig()
        assert config == AnsibleTestConfig()

        config = load_ansible_test_config(ignore_errors=True)
        assert config.modules.python_requires == "default"
        assert config.modules == ModulesConfig()
        assert config == AnsibleTestConfig()

        store_yaml_file(config_yml, {"modules": {"python_requires": []}})
        with pytest.raises(ValueError):
            load_ansible_test_config()
        with pytest.raises(ValueError):
            load_ansible_test_config(accept_missing=True)
        config = load_ansible_test_config(ignore_errors=True)
        assert config.modules.python_requires == "default"
        assert config.modules == ModulesConfig()
        assert config == AnsibleTestConfig()

        store_yaml_file(config_yml, {"modules": {"python_requires": "asdf"}})
        config = load_ansible_test_config()
        assert config.modules.python_requires == "asdf"


def test_get_min_python_version() -> None:
    assert (
        get_min_python_version(
            AnsibleTestConfig(modules=ModulesConfig(python_requires="default"))
        )
        == "default"
    )
    assert (
        get_min_python_version(
            AnsibleTestConfig(modules=ModulesConfig(python_requires="controller"))
        )
        == "controller"
    )

    with pytest.raises(
        ValueError,
        match="^%s$"
        % re.escape("Invalid specifier set in modules.python_requires: 'asdf'"),
    ):
        get_min_python_version(
            AnsibleTestConfig(modules=ModulesConfig(python_requires="asdf"))
        )
    assert (
        get_min_python_version(
            AnsibleTestConfig(modules=ModulesConfig(python_requires="asdf")),
            ignore_errors=True,
        )
        == "default"
    )

    matcher = get_min_python_version(
        AnsibleTestConfig(modules=ModulesConfig(python_requires=">=3.8"))
    )
    assert callable(matcher)
    assert not matcher(Version.parse("2.6"))
    assert not matcher(Version.parse("2.7"))
    assert not matcher(Version.parse("3.4"))
    assert not matcher(Version.parse("3.5"))
    assert not matcher(Version.parse("3.6"))
    assert not matcher(Version.parse("3.7"))
    assert matcher(Version.parse("3.8"))
    assert matcher(Version.parse("3.9"))
    assert matcher(Version.parse("3.10"))
    assert matcher(Version.parse("3.11"))
    assert matcher(Version.parse("3.12"))

    matcher = get_min_python_version(
        AnsibleTestConfig(
            modules=ModulesConfig(python_requires=">=3.8,<3.11,!=3.9,!=3.8.1")
        )
    )
    assert callable(matcher)
    assert not matcher(Version.parse("2.6"))
    assert not matcher(Version.parse("2.7"))
    assert not matcher(Version.parse("3.4"))
    assert not matcher(Version.parse("3.5"))
    assert not matcher(Version.parse("3.6"))
    assert not matcher(Version.parse("3.7"))
    assert matcher(Version.parse("3.8"))
    assert not matcher(Version.parse("3.9"))
    assert matcher(Version.parse("3.10"))
    assert not matcher(Version.parse("3.11"))
    assert not matcher(Version.parse("3.12"))
