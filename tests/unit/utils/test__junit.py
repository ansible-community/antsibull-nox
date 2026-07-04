# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

import datetime
import typing as t

import pytest

from antsibull_nox.utils._junit import (
    Error,
    Failure,
    Skipped,
)
from antsibull_nox.utils._junit import Testcase as _Testcase
from antsibull_nox.utils._junit import Testsuite as _Testsuite
from antsibull_nox.utils._junit import (
    serialize_junit_xml,
)


def _create_testsuite_1() -> _Testsuite:
    result = _Testsuite(name="test suite one")
    result.timestamp = datetime.datetime(
        year=2026,
        month=1,
        day=14,
        hour=23,
        minute=59,
        second=59,
        microsecond=1234,
        tzinfo=datetime.timezone.utc,
    )
    result.children.append(child := _Testcase(name="test case one"))
    child.stats.tests = 1
    child.stats.assertions = 2
    child.stats.time = datetime.timedelta(seconds=15)
    result.children.append(child := _Testcase(name="test case two"))
    child.stats.disabled = 15
    child.stats.errors = 3
    child.stats.failures = 1
    child.stats.skipped = 2
    child.stats.tests = 1
    child.stats.time = datetime.timedelta(seconds=17)
    child.skipped = Skipped()
    child.failure = Failure(message=None)
    child.error = Error(message=None)
    result.children.append(child := _Testcase(name="test case three"))
    child.skipped = Skipped(message="Skipped")
    child.failure = Failure(
        message="A test failure", type="blah", description="1\n 2\n3"
    )
    child.error = Error(
        message="A fatal test error", type="blubb", description="e\n  f\ng"
    )
    child.stdout = "o1\n   o2\no3"
    child.stderr = "e1\ne2\n e3"
    return result


def _create_testsuite_2() -> _Testsuite:
    result = _Testsuite(name="test suite two")
    result.url = "https://example.com/"
    return result


# noqa: E501
SERIALIZATION_TEST_CASES: list[tuple[list[_Testsuite], dict[str, t.Any], str]] = [
    (
        [],
        {"name": "hello world"},
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world"/>""",
    ),
    (
        [],
        {
            "name": "hello world",
            "timestamp": datetime.datetime(
                year=2026,
                month=1,
                day=14,
                hour=23,
                minute=59,
                second=58,
                microsecond=123456,
                tzinfo=datetime.timezone.utc,
            ),
        },
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world" timestamp="2026-01-14T23:59:58+00:00"/>""",
    ),
    (
        [],
        {"name": "hello world", "pretty_print": True},
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world"/>
""",
    ),
    (
        [
            _Testsuite(name="hello"),
        ],
        {"name": "hello world", "pretty_print": True},
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world">
  <testsuite name="hello"/>
</testsuites>
""",
    ),
    (
        [
            _Testsuite(name="hello"),
            _create_testsuite_1(),
            _create_testsuite_2(),
        ],
        {
            "name": "hello world",
            "timestamp": datetime.datetime(
                year=2026,
                month=1,
                day=14,
                hour=23,
                minute=59,
                second=58,
                microsecond=123456,
                tzinfo=datetime.timezone.utc,
            ),
            "pretty_print": True,
        },
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world" timestamp="2026-01-14T23:59:58+00:00" disabled="15" errors="3" failures="1" skipped="2" tests="2" assertions="2" time="32.000">
  <testsuite name="hello"/>
  <testsuite name="test suite one" timestamp="2026-01-14T23:59:59+00:00" disabled="15" errors="3" failures="1" skipped="2" tests="2" assertions="2" time="32.000">
    <testcase name="test case one" tests="1" assertions="2" time="15.000"/>
    <testcase name="test case two" disabled="15" errors="3" failures="1" skipped="2" tests="1" time="17.000">
      <skipped type="skipped"/>
      <failure type="failure"/>
      <error type="error"/>
    </testcase>
    <testcase name="test case three">
      <skipped type="skipped" message="Skipped"/>
      <failure type="blah" message="A test failure">1
 2
3</failure>
      <error type="blubb" message="A fatal test error">e
  f
g</error>
      <system-out>o1
   o2
o3</system-out>
      <system-err>e1
e2
 e3</system-err>
    </testcase>
  </testsuite>
  <testsuite name="test suite two" url="https://example.com/"/>
</testsuites>
""",
    ),
]


@pytest.mark.parametrize(
    "testsuites, kwargs, expected_output", SERIALIZATION_TEST_CASES
)
def test_serialization(
    testsuites: list[_Testsuite], kwargs: dict[str, t.Any], expected_output: str
) -> None:
    assert serialize_junit_xml(testsuites, **kwargs) == expected_output
