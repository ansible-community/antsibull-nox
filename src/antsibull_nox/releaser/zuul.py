# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Zuul helpers.
"""

from __future__ import annotations

import dataclasses
import datetime
import typing as t
from collections.abc import Mapping, Sequence

from ._http import RequestsSession, quote, quote_kv

if t.TYPE_CHECKING:  # pragma: no cover
    ResultType = t.Literal[
        "SUCCESS", "RETRY", "RETRY_LIMIT", "SKIPPED", "POST_FAILURE", "NODE_FAILURE"
    ]

    _T = t.TypeVar("_T")


@dataclasses.dataclass
class BuildInfo:
    """
    Information on a Zuul build.
    """

    uuid: str
    result: ResultType | None
    execute_time: datetime.datetime | None
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    project: str
    ref: str


def _parse_time(value: str | None) -> datetime.datetime | None:
    if value is None:
        return None
    return datetime.datetime.fromisoformat(value)


def add_query(
    query: list[str], key: str, values: _T | Sequence[_T] | None, *, clazz: t.Type[_T]
) -> None:
    """
    Add quoted query key=value strings for given key and values.
    """
    if values is None:
        return
    if isinstance(values, clazz):
        values = [values]
    assert isinstance(values, Sequence)
    for value in values:
        query.append(quote_kv(key, str(value)))


class ZuulClient(RequestsSession):
    """
    Basic Zuul client.
    """

    def __init__(self, *, base_url: str, tenant: str) -> None:
        super().__init__()
        base_url = base_url.rstrip("/")
        self._base_url = f"{base_url}/api/tenant/{tenant}/"

    def _url(self, url: str, query: list[str] | None = None) -> str:
        url = f"{self._base_url}/{url}"
        if query:
            url = f"{url}?{'&'.join(query)}"
        return url

    @staticmethod
    def _build_info(data: t.Any) -> BuildInfo:
        if not isinstance(data, Mapping):
            raise ValueError(f"Expected mapping for build info, got {type(data)}")
        ref = data.get("ref")
        if not isinstance(ref, Mapping):
            raise ValueError(
                f"Expected mapping for 'ref' in build info, got {type(ref)}"
            )

        return BuildInfo(
            uuid=data["uuid"],
            result=data.get("result"),
            execute_time=_parse_time(data.get("execute_time")),
            start_time=_parse_time(data.get("start_time")),
            end_time=_parse_time(data.get("end_time")),
            ref=ref["ref"],
            project=ref["project"],
        )

    def list_builds(
        self,
        *,
        job_name: str | Sequence[str] | None = None,
        pipeline: str | Sequence[str] | None = None,
        project: str | Sequence[str] | None = None,
        ref: str | Sequence[str] | None = None,
        exclude_results: ResultType | Sequence[ResultType] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[BuildInfo]:
        """
        List all builds matching the filter parameters.
        """
        query: list[str] = []
        add_query(query, "job_name", job_name, clazz=str)
        add_query(query, "pipeline", pipeline, clazz=str)
        add_query(query, "project", project, clazz=str)
        add_query(query, "ref", ref, clazz=str)
        add_query(query, "exclude_result", exclude_results, clazz=str)
        query.append(quote_kv("skip", str(offset)))
        query.append(quote_kv("limit", str(limit)))

        url = self._url("builds", query)
        r = self._get(url, expected=[200], timeout=30)
        try:
            data = r.json()
        except Exception as exc:
            raise ValueError(f"Error while parsing GET {url} response: {exc}") from exc
        if not isinstance(data, Sequence) or isinstance(data, str):
            raise ValueError(f"GET {url} response is not a list, but {type(data)}")
        return [self._build_info(elt) for elt in data]

    def get_build(self, *, uuid: str) -> BuildInfo | None:
        """
        Get information on a specific build.
        """
        url = self._url(f"build/{quote(uuid)}")
        # pylint: disable=duplicate-code
        r = self._get(url, expected=[200, 404], timeout=10)
        if r.status_code == 404:
            return None
        try:
            data = r.json()
        except Exception as exc:
            raise ValueError(f"Error while parsing GET {url} response: {exc}") from exc
        return self._build_info(data)


__all__ = ("ZuulClient",)
