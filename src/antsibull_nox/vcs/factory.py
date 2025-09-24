# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
VCS provider factory.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import VCS, VcsProvider
from .git import GitProvider

GIT_EXECUTABLE_ENV_VAR = "ANTSIBULL_GIT_EXECUTABLE"


def get_vcs_provider(vcs: VCS) -> VcsProvider:
    """
    Factory method for VcsProvider instances.
    """
    if vcs == "git":
        git_executable = os.environ.get(GIT_EXECUTABLE_ENV_VAR) or "git"
        return GitProvider(git_executable=Path(git_executable))

    raise RuntimeError(f"Internal error: unhandled VCS {vcs}")


__all__ = ("get_vcs_provider",)
