# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
VCS interfaces and types.
"""

from __future__ import annotations

import abc
import typing as t
from pathlib import Path


class VcsProvider(metaclass=abc.ABCMeta):
    """
    Provides an abstract interface to VCSes.
    """

    @abc.abstractmethod
    def find_repo_path(self, *, path: Path) -> Path | None:
        """
        Given a path, finds the associated repository path for this VCS,
        if there is one.
        """

    @abc.abstractmethod
    def get_current_branch(self, *, repo: Path) -> str | None:
        """
        Retrieve the current branch of the repository.

        If there is no current branch for some reason, ``None`` is returned.
        """

    @abc.abstractmethod
    def get_changes_compared_to(self, *, repo: Path, branch: str) -> list[Path]:
        """
        Retrieve a list of files and directories that have been added, changed, or removed.

        The returned paths are relative to ``repo``!
        """


VCS = t.Literal["git"]


__all__ = (
    "VcsProvider",
    "VCS",
)
