# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

import re
import typing as t
from pathlib import Path

import pytest
from antsibull_fileutils.yaml import store_yaml_file

from antsibull_nox.ansible import (
    _CURRENT_DEVEL_VERSION,
    _CURRENT_MILESTONE_VERSION,
    _MIN_SUPPORTED_VERSION,
    AnsibleCoreVersion,
    _read_requires_ansible,
    get_ansible_core_info,
    get_ansible_core_package_name,
    get_supported_core_versions,
)
from antsibull_nox.python import _PYTHON_VERSIONS_TO_TRY
from antsibull_nox.utils import Version, version_range

from .utils import chdir


def test_check_devel_version() -> None:
    assert get_ansible_core_info("devel").ansible_core_version == _CURRENT_DEVEL_VERSION


def test_check_milestone_version() -> None:
    assert (
        get_ansible_core_info("milestone").ansible_core_version
        == _CURRENT_MILESTONE_VERSION
    )


def test_unknown_core_version() -> None:
    prev = _MIN_SUPPORTED_VERSION.previous_minor_version()
    with pytest.raises(
        ValueError, match=f"^Unknown ansible-core version {re.escape(str(prev))}$"
    ):
        get_ansible_core_info(prev)


def test_all_versions() -> None:
    # Make sure we have information on all ansible-core versions from 2.9 up to devel/milestone
    min_version = _MIN_SUPPORTED_VERSION
    max_version = max(_CURRENT_DEVEL_VERSION, _CURRENT_MILESTONE_VERSION)
    python_versions: set[Version] = set()
    for version in version_range(min_version, max_version, inclusive=True):
        info = get_ansible_core_info(version)
        assert info.ansible_core_version == version
        python_versions.update(info.controller_python_versions)
        python_versions.update(info.remote_python_versions)

    # Make sure that we know how to look for all Python versions that are in use
    for python_version in sorted(python_versions):
        assert python_version in _PYTHON_VERSIONS_TO_TRY

    # Make sure that we have all intermediate Python versions
    all_py3 = [
        python_version
        for python_version in python_versions
        if python_version.major == 3
    ]
    min_py3 = min(all_py3)
    max_py3 = max(all_py3)
    for version in version_range(min_py3, max_py3, inclusive=True):
        assert version in _PYTHON_VERSIONS_TO_TRY


GET_ANSIBLE_CORE_PAGAGE_NAME_DATA: list[
    tuple[AnsibleCoreVersion, dict[str, t.Any], str]
] = [
    (
        Version(2, 9),
        {},
        "https://github.com/ansible-community/eol-ansible/archive/stable-2.9.tar.gz",
    ),
    (
        Version(2, 9),
        {"source": "pypi"},
        "ansible>=2.9,<2.10",
    ),
    (
        Version(2, 10),
        {},
        "https://github.com/ansible-community/eol-ansible/archive/stable-2.10.tar.gz",
    ),
    (
        Version(2, 10),
        {"source": "pypi"},
        "ansible-base>=2.10,<2.11",
    ),
    (
        Version(2, 11),
        {},
        "https://github.com/ansible-community/eol-ansible/archive/stable-2.11.tar.gz",
    ),
    (
        Version(2, 11),
        {"source": "pypi"},
        "ansible-core>=2.11,<2.12",
    ),
    # Last EOL version
    (
        Version(2, 14),
        {},
        "https://github.com/ansible-community/eol-ansible/archive/stable-2.14.tar.gz",
    ),
    # First non-EOL version
    (
        Version(2, 15),
        {},
        "https://github.com/ansible/ansible/archive/stable-2.15.tar.gz",
    ),
    # devel
    (
        "devel",
        {},
        "https://github.com/ansible/ansible/archive/devel.tar.gz",
    ),
    (
        "devel",
        {"source": "pypi"},
        "https://github.com/ansible/ansible/archive/devel.tar.gz",
    ),
    # milestone
    (
        "milestone",
        {},
        "https://github.com/ansible/ansible/archive/milestone.tar.gz",
    ),
    (
        "milestone",
        {"source": "pypi"},
        "https://github.com/ansible/ansible/archive/milestone.tar.gz",
    ),
    (
        "milestone",
        {
            "branch_name": "refs/pull/84621/head",
            "ansible_repo": "ansible-community/eol-ansible",
        },
        "https://github.com/ansible-community/eol-ansible/archive/refs/pull/84621/head.tar.gz",
    ),
]


@pytest.mark.parametrize(
    "version, kwargs, expected_package_name",
    GET_ANSIBLE_CORE_PAGAGE_NAME_DATA,
)
def test_get_ansible_core_package_name(
    version: AnsibleCoreVersion, kwargs: dict[str, t.Any], expected_package_name: str
) -> None:
    assert get_ansible_core_package_name(version, **kwargs) == expected_package_name


GET_SUPPORTED_CORE_VERSIONS_DATA: list[
    tuple[str, dict[str, t.Any], list[AnsibleCoreVersion]]
] = [
    (
        ">= 2.9.10",
        {},
        [
            Version.parse("2.9"),
            Version.parse("2.10"),
            Version.parse("2.11"),
            Version.parse("2.12"),
            Version.parse("2.13"),
            Version.parse("2.14"),
            Version.parse("2.15"),
            Version.parse("2.16"),
            Version.parse("2.17"),
            Version.parse("2.18"),
            Version.parse("2.19"),
        ],
    ),
    (
        ">= 2.9.10, < 2.13",
        {"include_devel": True},
        [
            Version.parse("2.9"),
            Version.parse("2.10"),
            Version.parse("2.11"),
            Version.parse("2.12"),
            "devel",
        ],
    ),
    (
        ">= 2.9.10, < 2.16",
        {
            "min_version": Version.parse("2.11"),
            "max_version": Version.parse("2.14"),
            "except_versions": (Version.parse("2.13"),),
            "include_milestone": True,
            "include_devel": True,
        },
        [
            Version.parse("2.11"),
            Version.parse("2.12"),
            Version.parse("2.14"),
            "milestone",
            "devel",
        ],
    ),
    (
        ">= 2.9.10, < 2.11",
        {
            "except_versions": (Version.parse("2.9"), "milestone", "devel"),
            "include_milestone": True,
            "include_devel": True,
        },
        [
            Version.parse("2.10"),
        ],
    ),
]


def test__read_requires_ansible_fail(tmp_path: Path) -> None:
    meta = tmp_path / "meta"
    meta.mkdir()
    runtime_yml = meta / "runtime.yml"
    with chdir(tmp_path):
        _read_requires_ansible.cache_clear()  # added by @functools.cache
        with pytest.raises(ValueError, match="^Cannot open meta/runtime.yml$"):
            _read_requires_ansible()

        _read_requires_ansible.cache_clear()  # added by @functools.cache
        runtime_yml.mkdir()
        with pytest.raises(
            ValueError,
            match=(
                r"^Cannot parse meta/runtime.yml: \[Errno 21\]"
                " Is a directory: 'meta/runtime.yml'$"
            ),
        ):
            _read_requires_ansible()
        runtime_yml.rmdir()

        runtime_yml.write_text("{")
        _read_requires_ansible.cache_clear()  # added by @functools.cache
        with pytest.raises(
            ValueError,
            match="^Cannot parse meta/runtime.yml: while parsing a flow node",
        ):
            _read_requires_ansible()

        store_yaml_file(runtime_yml, {"requires_ansible": 123})
        _read_requires_ansible.cache_clear()  # added by @functools.cache
        with pytest.raises(
            ValueError,
            match="^meta/runtime.yml does not contain an 'requires_ansible' string$",
        ):
            _read_requires_ansible()

        store_yaml_file(runtime_yml, {"requires_ansible": []})
        _read_requires_ansible.cache_clear()  # added by @functools.cache
        with pytest.raises(
            ValueError,
            match="^meta/runtime.yml does not contain an 'requires_ansible' string$",
        ):
            _read_requires_ansible()

        store_yaml_file(runtime_yml, {})
        _read_requires_ansible.cache_clear()  # added by @functools.cache
        with pytest.raises(
            ValueError,
            match="^meta/runtime.yml does not contain an 'requires_ansible' string$",
        ):
            _read_requires_ansible()

        store_yaml_file(runtime_yml, {"requires_ansible": "<>"})
        _read_requires_ansible.cache_clear()  # added by @functools.cache
        with pytest.raises(
            ValueError,
            match=(
                "^meta/runtime.yml contains an invalid"
                " 'requires_ansible' string: Invalid specifier: '<>'$"
            ),
        ):
            _read_requires_ansible()


@pytest.mark.parametrize(
    "requires_ansible, kwargs, expected_version_list",
    GET_SUPPORTED_CORE_VERSIONS_DATA,
)
def test_get_supported_core_versions(
    requires_ansible: str,
    kwargs: dict[str, t.Any],
    expected_version_list: list[AnsibleCoreVersion],
    tmp_path: Path,
) -> None:
    meta = tmp_path / "meta"
    meta.mkdir()
    runtime_yml = meta / "runtime.yml"
    store_yaml_file(runtime_yml, {"requires_ansible": requires_ansible})
    with chdir(tmp_path):
        _read_requires_ansible.cache_clear()  # added by @functools.cache
        get_supported_core_versions.cache_clear()  # added by @functools.cache
        print(kwargs)
        version_list = get_supported_core_versions(**kwargs)
    assert version_list == expected_version_list
