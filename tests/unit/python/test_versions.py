# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

from __future__ import annotations

import sys
from pathlib import Path

from antsibull_nox.python.versions import (
    _LATEST_PYTHON_VERSION,
    get_installed_python_versions,
    get_recent_python_version,
)
from antsibull_nox.utils import Version

from ..utils import set_environ


def test__LATEST_PYTHON_VERSION() -> None:
    # Ensure that _LATEST_PYTHON_VERSION is at least as high as the latest Python version in CI
    vt = (_LATEST_PYTHON_VERSION.major, _LATEST_PYTHON_VERSION.minor)
    pvt = (sys.version_info.major, sys.version_info.minor)
    assert vt >= pvt


def fake_binary(path: Path, content: str) -> Path:
    path.write_text(content)
    path.chmod(0o700)
    return path


def fake_python_binary(path: Path, version: str) -> Path:
    return fake_binary(path, f"""#!/bin/bash\necho {version}\n""")


def test_get_installed_python_versions(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    with set_environ("PATH", str(bin_dir)):
        get_installed_python_versions.cache_clear()  # added by @functools.cache
        assert get_installed_python_versions() == {}

    py27 = fake_python_binary(bin_dir / "python2.7", "2.7")
    with set_environ("PATH", str(bin_dir)):
        get_installed_python_versions.cache_clear()  # added by @functools.cache
        assert get_installed_python_versions() == {Version(2, 7): py27}

    py27 = fake_python_binary(bin_dir / "python2.7", "2.7")
    py35 = fake_python_binary(bin_dir / "python3", "3.5")
    fake_binary(bin_dir / "python2", "#!/bin/bash\necho Foo\n")
    fake_binary(bin_dir / "python", "#!/bin/bash\nexit 1\n")
    with set_environ("PATH", str(bin_dir)):
        get_installed_python_versions.cache_clear()  # added by @functools.cache
        assert get_installed_python_versions() == {
            Version(2, 7): py27,
            Version(3, 5): py35,
        }


def test_get_recent_python_version() -> None:
    v30 = Version.parse("3.0")
    v39 = Version.parse("3.9")
    v310 = Version.parse("3.10")
    next = _LATEST_PYTHON_VERSION.next_minor_version()
    assert get_recent_python_version([v30, next]) == v30
    assert get_recent_python_version([v30, v39, next]) == v39
    assert get_recent_python_version([v30, v39, v310, next]) == v310
    assert get_recent_python_version([next]) == next
