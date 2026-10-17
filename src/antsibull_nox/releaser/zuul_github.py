# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Collection releasers.
"""

from __future__ import annotations

import datetime
import tempfile
import typing as t
from pathlib import Path

from semantic_version import Version

from ..config import ZuulGitHubReleaser as ZuulGitHubReleaserConfig
from .base import BaseReleaser, VerifyFailed
from .galaxy import GalaxyClient, ReleaseInfo
from .git import GitReleaser
from .ui import Retry, retry, wait_for
from .zuul import BuildInfo, ZuulClient

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from .ui import LogFunction


class ZuulGitHubReleaser(BaseReleaser, GitReleaser):
    """
    Releaser using Zuul + GitHub to publish to Ansible Galaxy.
    """

    def __init__(self, config: ZuulGitHubReleaserConfig) -> None:
        GitReleaser.__init__(self, config)
        self.config = config
        self.zuul_client = ZuulClient(config.zuul_base_url)
        self.galaxy_client = GalaxyClient(config.galaxy_base_url)

    def _get_done_build(self, build: BuildInfo) -> Callable[[LogFunction], bool]:
        def f(log: LogFunction) -> bool:
            log(f"Get status of build {build.uuid}...")
            try:
                latest_build = self.zuul_client.get_build(uuid=build.uuid)
            except ValueError as exc:
                log(f"  Error: {exc}")
                raise Retry() from None
            if latest_build is None:
                log(f"Build {build.uuid} vanished...")
                return False
            if latest_build.result is None:
                raise Retry()
            if latest_build.result == "SUCCESS":
                return True
            log(f"Build failed with status {latest_build.result}")
            return False

        return f

    def wait_until_released(
        self, *, namespace: str, name: str, version: Version, verify: bool
    ) -> None:
        """
        Wait for the release to appear.
        """
        tag = self.config.tag_format.replace("{version}", str(version))
        expected_ref = f"refs/tags/{tag}"

        def get_build(log: LogFunction) -> BuildInfo:
            log("Looking for Zuul builds...")
            try:
                builds = self.zuul_client.list_builds(
                    job_name="release-ansible-collection-galaxy",
                    pipeline="pre-release" if version.prerelease else "release",
                    project=self.config.project_name,
                    ref=expected_ref,
                    exclude_results=["SKIPPED", "RETRY", "RETRY_LIMIT"],
                )
            except ValueError as exc:
                log(f"  Error: {exc}")
                raise Retry() from None
            for build in builds:
                if build.result in ("SUCCESS", None):
                    return build
            raise Retry()

        def get_release(log: LogFunction) -> ReleaseInfo:
            log("Looking for Galaxy release...")
            try:
                release = self.galaxy_client.get_specific_release(
                    namespace, name, version
                )
                if release is not None:
                    return release
            except ValueError as exc:
                log(f"  Error: {exc}")
            raise Retry()

        # Wait for successful build
        while True:
            build = wait_for(get_build, interval=datetime.timedelta(seconds=30))
            if build.result == "SUCCESS":
                print("Found successful build")
                break
            if wait_for(
                self._get_done_build(build), interval=datetime.timedelta(seconds=10)
            ):
                break

        release = wait_for(get_release, interval=datetime.timedelta(seconds=10))
        if verify:
            print("Verifying...")
            self._verify(release, version)

    def _verify(self, release: ReleaseInfo, version: Version) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name)
            galaxy_tarball = tempdir / "galaxy.tar"
            retry(
                lambda: self.galaxy_client.download_release(release, galaxy_tarball),
                what="Downloading Galaxy tarball",
            )
            try:
                release.artifact.validate_path(galaxy_tarball)
            except ValueError as exc:
                raise VerifyFailed(
                    f"Validation of Galaxy tarball checksum failed: {exc}"
                ) from exc

            # TODO: validate files in tarball

            # TODO: create archive from tag, validate its contents against the manifest

        print("Release successfully verified.")

    def verify_release(self, *, namespace: str, name: str, version: Version) -> None:
        """
        Verify that the release has been released as expected.
        Raise ``ValueError`` if validation fails.
        """
        release = self.galaxy_client.get_specific_release(namespace, name, version)
        if release is None:
            raise ValueError(f"Cannot find release {version}")
        self._verify(release, version)


__all__ = ("ZuulGitHubReleaser",)
