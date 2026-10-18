# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
GitHub helpers.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
import typing as t
import webbrowser

from semantic_version import Version

from ..config import _GitHubReleaserFragment
from ._http import Forbidden, RequestsSession, Unauthorized, quote, quote_kv
from ._template import template_string
from .changelog import get_markdown_extract

_NUM_RETRIES = 3


class GitHubClient(RequestsSession):
    """
    Basic GitHub client.
    """

    def __init__(self, config: _GitHubReleaserFragment) -> None:
        super().__init__()
        self.__config = config
        self.__base_url = f"https://github.com/{config.github_org}/{config.github_repo}"
        self.__api_base_url = (
            f"https://api.github.com/repos/{config.github_org}/{config.github_repo}"
        )
        self.__token: str | None = None

    def __reset_token(self) -> None:
        self.__token = None

    @t.overload
    def __get_token(
        self, *, required: t.Literal[True] = True, reason: str | None = None
    ) -> str: ...

    @t.overload
    def __get_token(
        self,
        *,
        required: t.Literal[False],
        reason: str | None = None,
        do_not_ask: bool = False,
    ) -> str | None: ...

    def __get_token(
        self,
        *,
        required: bool = True,
        reason: str | None = None,
        do_not_ask: bool = False,
    ) -> str | None:
        if self.__token is not None:
            return self.__token

        # Try environment variable
        gh_token = os.environ.get("ANTSIBULL_NOX_GITHUB_TOKEN")
        if gh_token:
            self.__token = gh_token
            return gh_token

        # Ask user (if stdout is a TTY)
        if sys.stdout.isatty() and not do_not_ask:
            prompt = "GitHub token"
            if reason is not None:
                prompt = f"{prompt} for {reason}"
            if not required:
                prompt = f"{prompt} (press Ctrl+C to continue without token)"
            try:
                gh_token = getpass.getpass(prompt=f"{prompt}: ")
                if gh_token:
                    self.__token = gh_token
                    return gh_token
            except KeyboardInterrupt:
                print("Aborted.")
                print("Continuing without token...")

        if not required:
            return None
        raise ValueError("Cannot get hold of GitHub token!")

    def _create_release_api(
        self,
        *,
        token: str,
        tag: str,
        name: str,
        body: str,
        is_prerelease: bool,
        make_draft: bool,
        make_latest: bool,
        discussion_category_name: str | None,
    ) -> tuple[str | None, str | None]:
        # https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10#create-a-release
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        data = {
            "tag_name": tag,
            "name": name,
            "body": body,
            "draft": make_draft,
            "prerelease": is_prerelease,
            "make_latest": make_latest,
            "generate_release_notes": False,
            "discussion_category_name": discussion_category_name,
        }
        url = f"{self.__api_base_url}/releases"
        r = self._post(
            url, headers=headers, data=json.dumps(data), timeout=60, expected=[201]
        )
        try:
            result = r.json()
        except Exception as exc:
            raise ValueError(f"Error while parsing POST {url} response: {exc}") from exc
        html_url = result.get("html_url")
        if not isinstance(html_url, str):
            raise ValueError(
                f"Error while parsing POST {url} response:"
                f" 'html_url' is not a string, but {type(html_url)}"
            )
        return html_url, result.get("discussion_url")

    def create_release(
        self,
        *,
        version: Version,
        make_draft: bool = True,
        make_latest: bool = False,
        discussion_category_name: str | None = None,
        without_token: bool = False,
    ) -> tuple[str | None, str | None]:
        """
        Create a GitHub release in the UI.
        """
        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )
        variables = {
            "version": str(version),
            "repository_url": self.__base_url,
            "branch": self.__config.git_release_branch,
            "changelog": get_markdown_extract(version=version),
        }
        name = template_string(self.__config.github_release_title, variables=variables)
        body = template_string(self.__config.github_release_body, variables=variables)
        is_prerelease = bool(version.prerelease)

        if not without_token:
            token = self.__get_token(required=False, reason="create release")
            for retry in range(_NUM_RETRIES):
                if token is None:
                    break
                do_retry = retry + 1 < _NUM_RETRIES
                try:
                    return self._create_release_api(
                        token=token,
                        tag=tag,
                        name=name,
                        body=body,
                        is_prerelease=is_prerelease,
                        make_draft=make_draft,
                        make_latest=make_latest,
                        discussion_category_name=discussion_category_name,
                    )
                except Forbidden, Unauthorized:
                    if token is None:
                        print("Authorization required...")
                    else:
                        print("Token not authorized!")
                    self.__reset_token()
                    if do_retry:
                        token = self.__get_token(
                            required=False, reason="create release"
                        )
                except ValueError as exc:
                    suffix = ". Retrying..." if do_retry else ""
                    print(f"Unexpected error: {exc}{suffix}")
            print("Trying alternative approach...")

        # Create URL
        params = [
            quote_kv("tag", tag),
            quote_kv("title", name),
            quote_kv("body", body),
            quote_kv("prerelease", json.dumps(is_prerelease)),
        ]
        url = f"{self.__base_url}/releases/new?{'&'.join(params)}"
        try:
            webbrowser.open(url)
            return None, None
        except webbrowser.Error as exc:
            raise ValueError(
                f"Cannot create release by opening URL in webbrowser: {exc}\n\nURL: {url}"
            ) from exc

    def _has_tag_api(self, *, token: str | None, tag: str) -> bool:
        # https://docs.github.com/en/rest/git/tags?apiVersion=2026-03-10#get-a-tag
        url = f"{self.__api_base_url}/git/ref/tags/{quote(tag)}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        r = self._get(url, headers=headers, timeout=10, expected=[200, 404])
        return r.status_code == 200

    def has_tag(
        self,
        *,
        version: Version,
        without_token: bool = False,
    ) -> bool:
        """
        Check whether a tag exists.
        """
        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )

        # In the first iteration, do not ask for a token; first try
        token = (
            None if without_token else self.__get_token(required=False, do_not_ask=True)
        )
        retry = 0
        while True:
            retry += 1
            do_retry = retry < _NUM_RETRIES
            try:
                return self._has_tag_api(token=token, tag=tag)
            except Forbidden, Unauthorized:
                if token is None:
                    print("Authorization required...")
                    if without_token:
                        raise
                else:
                    print("Token not authorized!")
                if not do_retry:
                    raise
                self.__reset_token()
                token = self.__get_token(
                    required=False, reason="verify existence of tag"
                )
            except ValueError as exc:
                suffix = ". Retrying..." if do_retry else ""
                print(f"Unexpected error: {exc}{suffix}")
                if not do_retry:
                    raise

    def _get_tag_release_url_api(self, *, token: str | None, tag: str) -> str | None:
        # https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10#get-a-release-by-tag-name
        url = f"{self.__api_base_url}/releases/tags/{quote(tag)}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        r = self._get(url, headers=headers, timeout=10, expected=[200, 404])
        if r.status_code == 404:
            return None
        try:
            result = r.json()
        except Exception as exc:
            raise ValueError(f"Error while parsing GET {url} response: {exc}") from exc
        html_url = result.get("html_url")
        if not isinstance(html_url, str):
            raise ValueError(
                f"Error while parsing GET {url} response:"
                f" 'html_url' is not a string, but {type(html_url)}"
            )
        return html_url

    def get_tag_release_url(
        self,
        *,
        version: Version,
        without_token: bool = False,
    ) -> str | None:
        """
        Check whether a release for that tag exists.
        """
        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )

        # In the first iteration, do not ask for a token; first try
        token = (
            None if without_token else self.__get_token(required=False, do_not_ask=True)
        )
        retry = 0
        while True:
            retry += 1
            do_retry = retry < _NUM_RETRIES
            try:
                return self._get_tag_release_url_api(token=token, tag=tag)
            except Forbidden, Unauthorized:
                if token is None:
                    print("Authorization required...")
                    if without_token:
                        raise
                else:
                    print("Token not authorized!")
                if not do_retry:
                    raise
                self.__reset_token()
                token = self.__get_token(
                    required=False, reason="verify existence of tag"
                )
            except ValueError as exc:
                suffix = ". Retrying..." if do_retry else ""
                print(f"Unexpected error: {exc}{suffix}")
                if not do_retry:
                    raise
