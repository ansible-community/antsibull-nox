# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

import re
import urllib.request

from antsibull_nox.ansible import _CURRENT_DEVEL_VERSION as CURRENT_DEVEL_VERSION
from antsibull_nox.ansible import (
    _CURRENT_MILESTONE_VERSION as CURRENT_MILESTONE_VERSION,
)
from antsibull_nox.utils import Version

_ANSIBLE_CORE_VERSION_REGEX = re.compile(r"""__version__ = (?:'([^']+)'|"([^"]+)")""")


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
    assert get_branch_version("devel") == CURRENT_DEVEL_VERSION


def test_check_milestone_version() -> None:
    assert get_branch_version("milestone") == CURRENT_MILESTONE_VERSION
