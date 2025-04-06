# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

import typing as t

import pytest

from antsibull_nox.ansible import _CURRENT_DEVEL_VERSION as CURRENT_DEVEL_VERSION
from antsibull_nox.ansible import (
    _CURRENT_MILESTONE_VERSION as CURRENT_MILESTONE_VERSION,
)
from antsibull_nox.ansible import (
    AnsibleCoreVersion,
    get_ansible_core_info,
    get_ansible_core_package_name,
)
from antsibull_nox.python import _PYTHON_VERSIONS_TO_TRY
from antsibull_nox.utils import Version, version_range


def test_check_devel_version() -> None:
    assert get_ansible_core_info("devel").ansible_core_version == CURRENT_DEVEL_VERSION


def test_check_milestone_version() -> None:
    assert (
        get_ansible_core_info("milestone").ansible_core_version
        == CURRENT_MILESTONE_VERSION
    )


def test_unknown_core_version() -> None:
    with pytest.raises(ValueError, match=r"^Unknown ansible-core version 2\.8$"):
        get_ansible_core_info(Version.parse("2.8"))


def test_all_versions() -> None:
    # Make sure we have information on all ansible-core versions from 2.9 up to devel/milestone
    min_version = Version(2, 9)
    max_version = max(CURRENT_DEVEL_VERSION, CURRENT_MILESTONE_VERSION)
    python_versions = set()
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
]


@pytest.mark.parametrize(
    "version, kwargs, expected_package_name",
    GET_ANSIBLE_CORE_PAGAGE_NAME_DATA,
)
def test_get_ansible_core_package_name(
    version: AnsibleCoreVersion, kwargs: dict[str, t.Any], expected_package_name: str
) -> None:
    assert get_ansible_core_package_name(version, **kwargs) == expected_package_name
