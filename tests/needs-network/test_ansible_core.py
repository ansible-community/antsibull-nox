# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

import json
import re
import urllib.error
import urllib.request

from antsibull_nox.ansible import (
    _ANSIBLE_EOL_MAX_VERSION,
    _ANSIBLE_EOL_REPO,
    _CURRENT_DEVEL_VERSION,
    _CURRENT_MILESTONE_VERSION,
)
from antsibull_nox.utils import Version

_ANSIBLE_CORE_VERSION_REGEX = re.compile(r"""__version__ = (?:'([^']+)'|"([^"]+)")""")
_EOL_ANSIBLE_BRANCH_TEST_URL = (
    "https://raw.githubusercontent.com/{repo}/refs/heads/stable-{version}/README.md"
)

# You can get this value from https://github.com/ansible/ansible/commits/milestone.
# One this changes, information src/antsibull_nox/ansible.py might need to be updated.
_MILESTONE_LAST_COMMIT = "726e8d6548c24bac62b4cbd62ea5c3fd3acefc80"


def get_branch_version(branch_name: str) -> Version:
    url = (
        "https://raw.githubusercontent.com/ansible/ansible/"
        f"refs/heads/{branch_name}/lib/ansible/release.py"
    )
    release_py = urllib.request.urlopen(url).read().decode("utf-8")
    m = _ANSIBLE_CORE_VERSION_REGEX.search(release_py)
    if not m:
        raise ValueError(f"Cannot find ansible-core version in {url}:\n{release_py}")
    return Version.parse(m.group(1) or m.group(2))


def test_check_devel_version() -> None:
    assert get_branch_version("devel") == _CURRENT_DEVEL_VERSION


def test_check_milestone_version() -> None:
    assert get_branch_version("milestone") == _CURRENT_MILESTONE_VERSION


def does_exist(url: str) -> int:
    try:
        request = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"))
        request.close()
        return 200 <= request.status < 300
    except urllib.error.HTTPError as exc:
        if exc.status == 404:
            return False
        raise


def test_check_eol_ansible() -> None:
    max_url = _EOL_ANSIBLE_BRANCH_TEST_URL.format(
        repo=_ANSIBLE_EOL_REPO, version=_ANSIBLE_EOL_MAX_VERSION
    )
    assert does_exist(max_url) is True

    next_version = _ANSIBLE_EOL_MAX_VERSION.next_minor_version()
    next_max_url = _EOL_ANSIBLE_BRANCH_TEST_URL.format(
        repo=_ANSIBLE_EOL_REPO, version=next_version
    )
    assert does_exist(next_max_url) is False


def test_check_latest_milestone_commit() -> None:
    url = "https://api.github.com/repos/ansible/ansible/commits/milestone"
    data = json.loads(urllib.request.urlopen(url).read().decode("utf-8"))
    assert data.get("sha") == _MILESTONE_LAST_COMMIT
