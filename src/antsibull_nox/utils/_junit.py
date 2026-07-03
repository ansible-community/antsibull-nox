# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
JUnit XML support.
"""

from __future__ import annotations

import dataclasses
import datetime
import typing as t

from ._xml import Node as _Node
from ._xml import Text as _Text

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

    _T = t.TypeVar("_T")


def _add(first: _T | None, second: _T | None) -> _T | None:
    if first is None:
        return second
    if second is None:
        return first
    return first + second  # type: ignore[operator]


def _timestamp(timestamp: datetime.datetime) -> str:
    return timestamp.replace(microsecond=0).isoformat()


@dataclasses.dataclass
class Stats:
    """
    Statistics about a test case or test suite.
    """

    disabled: int | None = None
    errors: int | None = None
    failures: int | None = None
    skipped: int | None = None
    tests: int | None = None
    assertions: int | None = None
    time: datetime.timedelta | None = None

    def add(self, other: Stats) -> t.Self:
        """
        Add the other ``Stats`` object to this one.
        """
        self.disabled = _add(self.disabled, other.disabled)
        self.errors = _add(self.errors, other.errors)
        self.failures = _add(self.failures, other.failures)
        self.skipped = _add(self.skipped, other.skipped)
        self.tests = _add(self.tests, other.tests)
        self.assertions = _add(self.assertions, other.assertions)
        self.time = _add(self.time, other.time)
        return self

    def _add_to_node(self, node: _Node) -> None:
        if self.disabled is not None:
            node.set("disabled", str(self.disabled))
        if self.errors is not None:
            node.set("errors", str(self.errors))
        if self.failures is not None:
            node.set("failures", str(self.failures))
        if self.skipped is not None:
            node.set("skipped", str(self.skipped))
        if self.tests is not None:
            node.set("tests", str(self.tests))
        if self.assertions is not None:
            node.set("assertions", str(self.assertions))
        if self.time is not None:
            time_in_seconds = self.time.total_seconds()
            node.set("time", f"{time_in_seconds:.3f}")


class Testsuite:
    """
    A test suite.
    """

    def __init__(self, *, name: str) -> None:
        self.name = name
        self.children: list[Testsuite | Testcase] = []
        self.timestamp: datetime.datetime | None = None
        self.url: str | None = None

    def _serialize(self) -> tuple[_Node, Stats]:
        node = _Node("testsuite")
        node.set("name", self.name)
        if self.timestamp is not None:
            node.set("timestamp", _timestamp(self.timestamp))
        if self.url is not None:
            node.set("url", self.url)
        stats = Stats()
        for child in self.children:
            # pylint: disable-next=protected-access
            child_node, child_stats = child._serialize()
            node.append(child_node)
            stats.add(child_stats)
        stats._add_to_node(node)  # pylint: disable=protected-access
        return node, stats


@dataclasses.dataclass
class Skipped:
    """
    A skipped test case.
    """

    message: str | None = None

    def _serialize(self) -> _Node:
        node = _Node("skipped")
        node.set("type", "skipped")
        if self.message is not None:
            node.set("message", self.message)
        return node


@dataclasses.dataclass
class Failure:
    """
    A (regular) failure of a test case.
    """

    message: str | None
    type: str | None = None
    description: str | None = None

    def _serialize(self) -> _Node:
        node = _Node("failure")
        node.set("type", self.type or "failure")
        if self.message is not None:
            node.set("message", self.message)
        if self.description:
            node.append(_Text(self.description))
        return node


@dataclasses.dataclass
class Error:
    """
    An unexpected error during execution of a test case.
    """

    message: str | None
    type: str | None = None
    description: str | None = None

    def _serialize(self) -> _Node:
        node = _Node("error")
        node.set("type", self.type or "error")
        if self.message is not None:
            node.set("message", self.message)
        if self.description:
            node.append(_Text(self.description))
        return node


class Testcase:
    """
    A test case.
    """

    def __init__(self, *, name: str) -> None:
        self.name = name
        self.stats = Stats()

        # The following should always be set together with values in self.stats!
        self.failure: Failure | None = None
        self.error: Error | None = None
        self.skipped: Skipped | None = None

        self.stdout: str | None = None
        self.stderr: str | None = None

    def _serialize(self) -> tuple[_Node, Stats]:
        node = _Node("testcase")
        node.set("name", self.name)
        if self.skipped:
            node.append(self.skipped._serialize())  # pylint: disable=protected-access
        if self.failure:
            node.append(self.failure._serialize())  # pylint: disable=protected-access
        if self.error:
            node.append(self.error._serialize())  # pylint: disable=protected-access
        if self.stdout:
            node.append_node("system-out").append(_Text(self.stdout))
        if self.stderr:
            node.append_node("system-err").append(_Text(self.stderr))
        self.stats._add_to_node(node)  # pylint: disable=protected-access
        return node, self.stats


def serialize_junit_xml(
    testsuites: Sequence[Testsuite],
    *,
    name: str,
    timestamp: datetime.datetime | None = None,
    pretty_print: bool = False,
) -> str:
    """
    Given a list of test suites, serializes them as a JUnit XML file.
    """
    root = _Node("testsuites")
    root.set("name", name)
    if timestamp is not None:
        root.set("timestamp", _timestamp(timestamp))
    stats = Stats()
    for testsuite in testsuites:
        ts_node, ts_stats = testsuite._serialize()  # pylint: disable=protected-access
        root.append(ts_node)
        stats.add(ts_stats)
    stats._add_to_node(root)  # pylint: disable=protected-access
    return root.serialize(pretty_print=pretty_print, indent="  ")


__all__ = (
    "Error",
    "Failure",
    "Skipped",
    "Stats",
    "Testsuite",
    "Testcase",
    "serialize_junit_xml",
)
