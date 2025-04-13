# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

import contextlib
import os
import typing as t
from pathlib import Path

from antsibull_nox.python import get_installed_python_versions
from antsibull_nox.utils import Version


@contextlib.contextmanager
def set_environ(env_var: str, value: str) -> t.Iterator[None]:
    old_value = os.environ.get(env_var)
    try:
        os.environ[env_var] = value
        yield
    finally:
        if old_value is None:
            os.environ.pop(env_var, None)
        else:
            os.environ[env_var] = old_value


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
