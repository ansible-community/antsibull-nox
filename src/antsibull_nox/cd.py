# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Change detection specific code.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

from .config import VCS as VCSConfig
from .config import Config
from .vcs import VCS, VcsProvider
from .vcs.factory import get_vcs_provider

_ENABLE_CD_ENV_VAR = "ANTSIBULL_CHANGE_DETECTION"
_BASE_BRANCH_ENV_VAR = "ANTSIBULL_BASE_BRANCH"


class _CDConfig:
    vcs: VCS
    provider: VcsProvider
    repo: Path
    base_branch: str
    config_dir_is_repo_dir: bool

    def __init__(self, *, config_path: Path, vcs_config: VCSConfig) -> None:
        self.vcs = vcs_config.vcs
        self.provider = get_vcs_provider(self.vcs)
        path = config_path.parent
        repo = self.provider.find_repo_path(path=path)
        if repo is None:
            raise ValueError(f"Cannot find {self.vcs} repository for {path}")
        self.repo = repo
        self.config_dir_is_repo_dir = repo.absolute() == config_path.parent.absolute()
        self.base_branch = vcs_config.development_branch
        env_base_branch = os.environ.get(_BASE_BRANCH_ENV_VAR)
        if env_base_branch:
            self.base_branch = env_base_branch


_cd_initialized = False
_cd_config: _CDConfig | None = None


def init_cd(
    *,
    config: Config,
    config_path: Path,
    force: bool = False,
    ignore_previous_calls: bool = False,
) -> None:
    """
    Initialize data structures so that the other change detection
    functionality works.
    """
    # We want global context due to the way nox works.
    global _cd_initialized, _cd_config  # pylint: disable=global-statement

    if _cd_initialized and not ignore_previous_calls:
        raise ValueError("init_cd() has already been called!")

    if config.vcs is None:
        _cd_config = None
        _cd_initialized = True
        return

    if not force:
        value = (os.environ.get(_ENABLE_CD_ENV_VAR) or "").lower()
        if value != "true":
            _cd_config = None
            _cd_initialized = True
            return

    _cd_config = _CDConfig(config_path=config_path, vcs_config=config.vcs)
    _cd_initialized = True


def _check_initialized() -> None:
    if not _cd_initialized:
        raise RuntimeError("Internal error: init_cd() has not been called!")


def supports_cd() -> bool:
    """
    Determines whether a antsibull-nox configuration supports CD.
    """
    _check_initialized()
    return _cd_config is not None


def get_vcs_name() -> VCS | None:
    """
    Provide the configured CVS for change detection.

    Returns ``None`` if ``supports_cd() == False``.
    """
    _check_initialized()
    return _cd_config.vcs if _cd_config else None


def get_base_branch() -> str | None:
    """
    Provide the base branch for change detection.

    Returns ``None`` if ``supports_cd() == False``.
    """
    _check_initialized()
    return _cd_config.base_branch if _cd_config else None


def is_config_dir_the_repo_dir() -> bool | None:
    """
    Figure out whether the config dir (the directory containing
    ``antsibull-nox.toml``) is the repository's root directory.

    Returns ``None`` if ``supports_cd() == False``.
    """
    _check_initialized()
    return _cd_config.config_dir_is_repo_dir if _cd_config else None


@functools.cache
def get_changes(*, relative_to: Path | None = None) -> list[Path] | None:
    """
    Acquire a list of changes.

    Returns ``None`` if change detection is not available.

    Returned paths are relative to ``relative_to``, or CWD if ``relative_to is None``.
    """
    _check_initialized()
    cd_config = _cd_config
    if not cd_config:
        return None
    changes = cd_config.provider.get_changes_compared_to(
        repo=cd_config.repo, branch=cd_config.base_branch
    )

    if relative_to is None:
        relative_to = Path.cwd()

    return [
        (cd_config.repo / path).relative_to(relative_to, walk_up=True)
        for path in changes
    ]


__all__ = (
    "supports_cd",
    "init_cd",
    "get_base_branch",
    "get_changes",
)
