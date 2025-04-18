# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""Tool to create initial configuration."""

from pathlib import Path

from .collection.search import GALAXY_YML
from .config import CONFIG_FILENAME
from .lint_config import NOXFILE_PY

NOXFILE_CONTENT = r"""
# The following metadata allows Python runners and nox to install the required
# dependencies for running this Python script:
#
# /// script
# dependencies = ["nox>=2025.02.09", "antsibull-nox"]
# ///

import sys

import nox


# We try to import antsibull-nox, and if that doesn't work, provide a more useful
# error message to the user.
try:
    import antsibull_nox
except ImportError:
    print("You need to install antsibull-nox in the same Python environment as nox.")
    sys.exit(1)


antsibull_nox.load_antsibull_nox_toml()


# Allow to run the noxfile with `python noxfile.py`, `pipx run noxfile.py`, or similar.
# Requires nox >= 2025.02.09
if __name__ == "__main__":
    nox.main()
"""

CONFIG_CONTENT = r"""
[sessions]

[sessions.lint]
# disable reformatting for now
run_isort = false

# disable reformatting for now
run_black = false

# Add more configuration settings here to adjust to your collection;
# see https://ansible.readthedocs.io/projects/antsibull-nox/config-file/#basic-linting-sessions

[sessions.docs_check]
# Add configuration settings here to adjust to your collection;
# see https://ansible.readthedocs.io/projects/antsibull-nox/config-file/#collection-documentation-check
"""


def create_initial_config(*, path: Path | None = None) -> None:
    """
    Write noxfile.py and antsibull-nox.toml for a collection.
    """
    if path is None:
        path = Path()

    galaxy_yml = path / GALAXY_YML
    if not galaxy_yml.is_file():
        raise ValueError(f"Cannot find {galaxy_yml}")

    noxfile = path / NOXFILE_PY
    config_file = path / CONFIG_FILENAME
    for file in (noxfile, config_file):
        if file.exists():
            raise ValueError(f"{file} already exists")

    noxfile.write_text(NOXFILE_CONTENT)
    config_file.write_text(CONFIG_CONTENT)
