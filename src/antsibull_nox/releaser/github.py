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

from semantic_version import Version

from ..config import _GitHubReleaserFragment
from ._http import RequestsSession
from ._template import template_string
from .changelog import get_markdown_extract


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

    def __get_token(self) -> str:
        if self.__token is not None:
            return self.__token

        # Try environment variable
        gh_token = os.environ.get("ANTSIBULL_NOX_GITHUB_TOKEN")
        if gh_token:
            self.__token = gh_token
            return gh_token

        # Ask user (if stdout is a TTY)
        if sys.stdout.isatty():
            gh_token = getpass.getpass(prompt="GitHub token: ")
            if gh_token:
                self.__token = gh_token
                return gh_token

        raise ValueError("Cannot get hold of GitHub token!")

    def create_release(
        self,
        *,
        version: Version,
        make_draft: bool = True,
        make_latest: bool = False,
        discussion_category_name: str | None = None,
    ) -> tuple[str, str | None]:
        """
        Create a GitHub release in the UI.
        """
        # https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10#create-a-release
        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )
        variables = {
            "version": str(version),
            "repository_url": self.__base_url,
            "branch": self.__config.git_release_branch,
            "changelog": get_markdown_extract(version=version),
        }
        data = {
            "tag_name": tag,
            "name": template_string(
                self.__config.github_release_title, variables=variables
            ),
            "body": template_string(
                self.__config.github_release_body, variables=variables
            ),
            "draft": make_draft,
            "prerelease": bool(version.prerelease),
            "make_latest": make_latest,
            "generate_release_notes": False,
            "discussion_category_name": discussion_category_name,
        }
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.__get_token()}",
            "X-GitHub-Api-Version": "2026-03-10",
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
