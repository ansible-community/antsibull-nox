# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
HTTP helpers.
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import requests

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

    _T = t.TypeVar("_T")


class RequestsSession(requests.Session):
    """
    Requests session with basic helpers.
    """

    def _catch_errors(self, *, method: str, url: str, action: Callable[[], _T]) -> _T:
        try:
            return action()
        except requests.Timeout as exc:
            raise ValueError(f"Timeout for {method} {url}: {exc}") from exc
        except requests.RequestException as exc:
            raise ValueError(f"Unexpected error for {method} {url}: {exc}") from exc

    def _check_status(
        self,
        *,
        method: str,
        url: str,
        response: requests.Response,
        expected: int | Sequence[int],
    ) -> None:
        if response.status_code not in (
            [expected] if isinstance(expected, int) else expected
        ):
            raise ValueError(
                f"Unexpected HTTP status {response.status_code} for {method} {url}"
            )

    def _get(
        self,
        url: str,
        *,
        expected: int | Sequence[int],
        headers: dict[str, str] | None = None,
        timeout: float | None,
        allow_redirects: bool = False,
    ) -> requests.Response:
        r = self._catch_errors(
            method="GET",
            url=url,
            action=lambda: self.get(
                url, headers=headers, timeout=timeout, allow_redirects=allow_redirects
            ),
        )
        self._check_status(method="GET", url=url, response=r, expected=expected)
        return r

    def _post(
        self,
        url: str,
        *,
        expected: int | Sequence[int],
        data: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None,
        allow_redirects: bool = False,
    ) -> requests.Response:
        r = self._catch_errors(
            method="POST",
            url=url,
            action=lambda: self.post(
                url,
                data=data,
                headers=headers,
                timeout=timeout,
                allow_redirects=allow_redirects,
            ),
        )
        self._check_status(method="POST", url=url, response=r, expected=expected)
        return r

    def _download_file(
        self, url: str, path: Path, *, allow_redirects: bool = False
    ) -> None:
        def download() -> None:
            try:
                with self.get(url, stream=True, allow_redirects=allow_redirects) as r:
                    if r.status_code != 200:
                        raise ValueError(
                            f"GET {url} resulted in unexpected status {r.status_code}"
                        )
                    with path.open("wb") as f:
                        for data in r.iter_content(chunk_size=65536):
                            f.write(data)
            except IOError as exc:
                raise ValueError(
                    f"I/O error while storing the result of GET {url} to {path}: {exc}"
                ) from exc

        self._catch_errors(method="GET", url=url, action=download)


__all__ = ("RequestsSession",)
