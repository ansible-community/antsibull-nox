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
from ._template import template_string
from .base import BaseReleaser, VerifyFailed
from .galaxy import (
    GalaxyClient,
    ReleaseInfo,
    ValidationError,
    extract_manifest_and_files_from_tarball,
    validate_tarball,
)
from .git import Git, GitReleaser
from .github import GitHubClient
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
        self.github_client = GitHubClient(config)

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
            log(f"Build {build.uuid} failed with status {latest_build.result}")
            return False

        return f

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
        tag = template_string(
            self.config.git_tag_format, variables={"version": str(version)}
        )
        expected_ref = f"refs/tags/{tag}"

        def get_build(log: LogFunction) -> BuildInfo:
            log("Looking for Zuul builds...")
            try:
                builds = self.zuul_client.list_builds(
                    job_name="release-ansible-collection-galaxy",
                    pipeline="pre-release" if version.prerelease else "release",
                    project=self.config.zuul_project_name,
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
            self._verify(
                release,
                namespace,
                name,
                version,
                validate_with_sources=validate_with_sources,
            )

    def _raise_errors_exception(self, errors: list[ValidationError]) -> None:
        if errors:
            error_list = "\n".join(
                [f"{error.ftype} {error.tarball_path}: {error}" for error in errors]
            )
            raise VerifyFailed(
                f"Failed to validate files in Galaxy collection tarball:\n{error_list}"
            )

    def _verify(
        self,
        release: ReleaseInfo,
        namespace: str,
        name: str,
        version: Version,
        validate_with_sources: bool,
    ) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name)
            galaxy_tarball = tempdir / "galaxy.tar"
            print("Downloading Galaxy tarball...")
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

            print("Extracting MANIFEST.json and FILES.json...")
            manifest, files = extract_manifest_and_files_from_tarball(galaxy_tarball)
            if manifest.collection_info.name != name:
                raise VerifyFailed(
                    "Galaxy tarball manifest's collection name is"
                    f" {manifest.collection_info.name!r}, but expected {name!r}."
                )
            if manifest.collection_info.namespace != namespace:
                raise VerifyFailed(
                    "Galaxy tarball manifest's collection namespace is"
                    f" {manifest.collection_info.namespace!r}, but expected {namespace!r}."
                )
            if manifest.collection_info.version != str(version):
                raise VerifyFailed(
                    "Galaxy tarball manifest's collection version is"
                    f" {manifest.collection_info.version!r}, but expected {version!r}."
                )

            # pylint: disable-next=fixme
            # TODO: more detailled validation against galaxy.yml

            print("Validate Galaxy tarball against FILES.json...")
            self._raise_errors_exception(
                validate_tarball(
                    galaxy_tarball,
                    files,
                    is_tgz=True,
                    is_galaxy_tarball=True,
                    prefix=None,
                )
            )

            if validate_with_sources:
                print("Validate CVS sources against FILES.json...")
                source_tarball = tempdir / "source.tar"
                source_prefix = self.create_release_tarball(
                    tarball_path=source_tarball, version=version
                )
                self._raise_errors_exception(
                    validate_tarball(
                        source_tarball,
                        files,
                        is_tgz=False,
                        is_galaxy_tarball=False,
                        prefix=source_prefix,
                    )
                )

        print("Release successfully verified.")

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
        Raise ``ValueError`` if validation fails.
        """
        release = self.galaxy_client.get_specific_release(namespace, name, version)
        if release is None:
            raise ValueError(f"Cannot find release {version}")
        self._verify(
            release,
            namespace,
            name,
            version,
            validate_with_sources=validate_with_sources,
        )

    def can_create_vcs_ui_release(self) -> bool:
        """
        Whether the VCS allows to create a release in its web UI.
        """
        return True

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
        if not self.github_client.has_tag(version=version, without_token=without_token):
            return None
        return self.github_client.get_tag_release_url(
            version=version, without_token=without_token
        )

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
        if not self.github_client.has_tag(version=version, without_token=without_token):
            raise ValueError(f"GitHub tag for {version} does not exist!")
        release_url = self.github_client.get_tag_release_url(
            version=version, without_token=without_token
        )
        if release_url is not None:
            raise ValueError(
                f"Release for GitHub tag {version} already exists: {release_url}"
            )
        if verify:
            self.verify_release(
                namespace=namespace,
                name=name,
                version=version,
                validate_with_sources=validate_with_sources,
            )
        html_url, _ = self.github_client.create_release(
            version=version,
            make_draft=make_draft,
            make_latest=make_latest,
            without_token=without_token,
        )
        return html_url

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
        # First check whether we have a local tag, and whether the release already exists
        if not self.has_vcs_release(version=version):
            raise ValueError(f"Release tag {version} does not exist locally!")
        release_url = self.github_client.get_tag_release_url(
            version=version, without_token=without_token
        )
        if release_url is not None:
            raise ValueError(
                f"Release for GitHub tag {version} already exists: {release_url}"
            )

        # Push tag if it doesn't exist yet
        has_remote_tag = self.github_client.has_tag(
            version=version, without_token=without_token
        )
        if not has_remote_tag or force:
            tag = template_string(
                self.config.git_tag_format, variables={"version": str(version)}
            )
            git = Git()
            if has_remote_tag:
                git.remove_remote_tag(
                    tag=tag, remote=self.config.github_upstream_remote
                )
            git.push_remote_tag(tag=tag, remote=self.config.github_upstream_remote)

        # Wait for the release to appear on Galaxy, and validate it (if not disabled)
        self.wait_until_released(
            namespace=namespace,
            name=name,
            version=version,
            verify=verify,
            validate_with_sources=validate_with_sources,
        )

        # Create VCS release and return URL
        html_url, _ = self.github_client.create_release(
            version=version,
            make_draft=make_draft,
            make_latest=make_latest,
            without_token=without_token,
        )
        return html_url


__all__ = ("ZuulGitHubReleaser",)
