# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Collection releasers base classes.
"""

from __future__ import annotations

import abc
from pathlib import Path

from semantic_version import Version

from ..collection.data import CollectionData


class VerifyFailed(ValueError):
    """
    Indicate that the verification failed (as opposed to other error during verification).
    """


class BaseVCSReleaser(metaclass=abc.ABCMeta):
    """
    Base releaser class for VCS part (prepare, create release in VCS).
    """

    @abc.abstractmethod
    def create_vcs_release(
        self, *, collection: CollectionData, version: Version
    ) -> None:
        """
        Create release in VCS.

        Ensure we're in the right branch, create release commit(s) and tag(s).
        """

    @abc.abstractmethod
    def create_release_tarball(
        self, *, tarball_path: Path, version: Version
    ) -> str | None:
        """
        Create tarball (.tar) of a tagged release. Return prefix that all entries have.
        """


class BaseReleaser(BaseVCSReleaser, metaclass=abc.ABCMeta):
    """
    Base releaser class.
    """

    @abc.abstractmethod
    def wait_until_released(
        self,
        *,
        namespace: str,
        name: str,
        version: Version,
        verify: bool,
        validate_with_sources: bool = True,
    ) -> None:
        """
        Wait for the release to appear.
        """

    @abc.abstractmethod
    def verify_release(
        self,
        *,
        namespace: str,
        name: str,
        version: Version,
        validate_with_sources: bool = True,
    ) -> None:
        """
        Verify that the release has been released as expected.
        Raise ``VerifyFailed`` if validation fails, and ``ValueError`` in case of other errors.
        """

    @abc.abstractmethod
    def can_create_vcs_ui_release(self) -> bool:
        """
        Whether the VCS allows to create a release in its web UI.
        """

    @abc.abstractmethod
    def create_vcs_ui_release(
        self,
        *,
        namespace: str,
        name: str,
        version: Version,
        make_draft: bool = True,
        make_latest: bool = False,
        verify: bool = True,
        validate_with_sources: bool = True,
    ) -> str | None:
        """
        Create release in the VCS's web UI.
        Return a URL to the release, if available.
        """


__all__ = ("BaseReleaser",)
