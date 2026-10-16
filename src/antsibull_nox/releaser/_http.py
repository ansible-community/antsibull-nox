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
    from collections.abc import Sequence


class RequestsSession(requests.Session):
    """
    Requests session with basic helpers.
    """

    def _get(
        self, url: str, *, expected: int | Sequence[int], timeout: float | None
    ) -> requests.Response:
        try:
            # Galaxy always redirects on the 'canonical' URLs, so follow redirects...
            r = self.get(url, timeout=timeout, allow_redirects=True)
        except requests.Timeout as exc:
            raise ValueError(f"Timeout for GET {url}: {exc}") from exc
        except requests.RequestException as exc:
            raise ValueError(f"Unexpected error for GET {url}: {exc}") from exc

        if r.status_code not in ([expected] if isinstance(expected, int) else expected):
            raise ValueError(f"Unexpected HTTP status {r.status_code} for GET {url}")
        return r

    def _download_file(self, url: str, path: Path) -> None:
        try:
            with self.get(url, stream=True, allow_redirects=True) as r:
                if r.status_code != 200:
                    raise ValueError(
                        f"GET {url} resulted in unexpected status {r.status_code}"
                    )
                with path.open("wb") as f:
                    for data in r.iter_content(chunk_size=65536):
                        f.write(data)
        except requests.Timeout as exc:
            raise ValueError(f"Timeout for GET {url}: {exc}") from exc
        except requests.RequestException as exc:
            raise ValueError(f"Unexpected error for GET {url}: {exc}") from exc
        except IOError as exc:
            raise ValueError(
                f"I/O error while storing the result of GET {url} to {path}: {exc}"
            ) from exc


__all__ = ("RequestsSession",)
