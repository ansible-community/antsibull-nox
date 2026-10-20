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
    def prepare_vcs_release(
        self, *, collection: CollectionData, version: Version, release_summary: str
    ) -> None:
        """
        Prepare a release in VCS.

        Ensure we're in the right branch, update version and create release summary,
        and then create preparation commit(s).
        """

    @abc.abstractmethod
    def has_vcs_release(self, *, version: Version) -> bool:
        """
        Check whether a release already exists in VCS.
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
    def create_release_source_tarball(
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
    def has_vcs_ui_release(
        self,
        *,
        namespace: str,
        name: str,
        version: Version,
        without_token: bool = False,
    ) -> str | None:
        """
        Check whether a release in the CVS's web UI already exists.
        If it does not, return ``None``.
        Otherwise, return a URL to the release if available, and an empty string otherwise.
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
        without_token: bool = False,
    ) -> str | None:
        """
        Create release in the VCS's web UI.
        Return a URL to the release, if available.
        """

    @abc.abstractmethod
    def publish_release(
        self,
        *,
        namespace: str,
        name: str,
        version: Version,
        make_draft: bool = True,
        make_latest: bool = False,
        verify: bool = True,
        validate_with_sources: bool = True,
        without_token: bool = False,
        force: bool = False,
    ) -> str | None:
        """
        Initiate release process (if available),
        wait for the release to happen,
        validate it, and create a VCS web UI release if possible.
        Return a URL to the release, if available.

        ``force=True`` forces initiation of the release process,
        assuming the VCS web UI release does not yet exist.
        This could happen by deleting the remote release tag and
        re-pushing it.
        """


__all__ = ("BaseReleaser",)
