# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

import datetime
import xml.parsers.expat
from pathlib import Path

import pytest

from antsibull_nox.utils._junit import (
    Error,
    Failure,
    Skipped,
    Stats,
)
from antsibull_nox.utils._junit import Testcase as _Testcase
from antsibull_nox.utils._junit import Testsuite as _Testsuite
from antsibull_nox.utils._junit_parser import (
    JUnitXML,
    _Parser,
    parse_junit_xml,
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
        tzinfo=datetime.timezone.utc,
    )
    result.stats = Stats(
        disabled=15,
        errors=3,
        failures=1,
        skipped=2,
        tests=2,
        assertions=2,
        time=datetime.timedelta(seconds=32),
    )
    result.children.append(_Testsuite(name="world", stats=Stats()))
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
    child.failure = Failure(message=None, type="failure")
    child.error = Error(message=None, type="error")
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
    result = _Testsuite(name="test suite two", stats=Stats())
    result.url = "https://example.com/"
    return result


# noqa: E501
DESERIALIZATION_TEST_CASES: list[tuple[str, JUnitXML]] = [
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world"/>""",
        JUnitXML(
            timestamp=None,
            name="hello world",
            stats=Stats(),
            testsuites=[],
        ),
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world">
  <random other="data">
    Foo Bar
    <foo/>
  </random>
</testsuites>""",
        JUnitXML(
            timestamp=None,
            name="hello world",
            stats=Stats(),
            testsuites=[],
        ),
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world" timestamp="2026-01-14T23:59:58+00:00"/>""",
        JUnitXML(
            timestamp=datetime.datetime(
                year=2026,
                month=1,
                day=14,
                hour=23,
                minute=59,
                second=58,
                tzinfo=datetime.timezone.utc,
            ),
            name="hello world",
            stats=Stats(),
            testsuites=[],
        ),
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world">
  <testsuite name="hello"/>
</testsuites>
""",
        JUnitXML(
            timestamp=None,
            name="hello world",
            stats=Stats(),
            testsuites=[
                _Testsuite(name="hello", stats=Stats()),
            ],
        ),
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world" timestamp="2026-01-14T23:59:58+00:00" disabled="15" errors="3" failures="1" skipped="2" tests="2" assertions="2" time="32.000">
  <testsuite name="hello"/>
  <testsuite name="test suite one" timestamp="2026-01-14T23:59:59+00:00" disabled="15" errors="3" failures="1" skipped="2" tests="2" assertions="2" time="32.000">
    <testsuite name="world"/>
    <testcase name="test case one" tests="1" assertions="2" time="15.000"/>
    <testcase name="test case two" disabled="15" errors="3" failures="1" skipped="2" tests="1" time="17.000">
      <skipped type="skipped"/>
      <failure type="failure"/>
      <error type="error"/>
      <random other="data"/>
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
    <random more="data"/>
  </testsuite>
  <testsuite name="test suite two" url="https://example.com/"/>
  <random last="data"/>
</testsuites>
""",
        JUnitXML(
            timestamp=datetime.datetime(
                year=2026,
                month=1,
                day=14,
                hour=23,
                minute=59,
                second=58,
                tzinfo=datetime.timezone.utc,
            ),
            name="hello world",
            stats=Stats(
                disabled=15,
                errors=3,
                failures=1,
                skipped=2,
                tests=2,
                assertions=2,
                time=datetime.timedelta(seconds=32),
            ),
            testsuites=[
                _Testsuite(name="hello", stats=Stats()),
                _create_testsuite_1(),
                _create_testsuite_2(),
            ],
        ),
    ),
]


@pytest.mark.parametrize("content, expected_output", DESERIALIZATION_TEST_CASES)
def test_deserialization(content: str, expected_output: JUnitXML) -> None:
    assert _Parser().parse(content.encode("utf-8")) == expected_output


DESERIALIZATION_FAIL_TEST_CASES: list[tuple[str, type[BaseException], str]] = [
    (
        "",
        ValueError,
        "^JUnit XML file must contain <testsuites> element$",
    ),
    (
        """<?xml version="1.1" encoding="utf-8"?>
""",
        ValueError,
        "^JUnit XML file must contain <testsuites> element$",
    ),
    (
        """<?xml version="1.1" encoding="utf-8"?>
<testsuites/>
<testsuites/>
""",
        xml.parsers.expat.ExpatError,
        "[jJ]unk after",
    ),
    (
        """<?xml version="1.1" encoding="utf-8"?>
<foobar/>
""",
        ValueError,
        "^JUnit XML file must have outer <testsuites> tag$",
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites timestamp="foobar"/>
""",
        ValueError,
        "^Cannot parse time stamp 'foobar': Invalid isoformat string: 'foobar'$",
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites time="foobar"/>
""",
        ValueError,
        "^Cannot parse time delta 'foobar': could not convert string to float: 'foobar'$",
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites errors="foobar"/>
""",
        ValueError,
        r"^Cannot parse integer 'foobar': invalid literal for int\(\) with base 10: 'foobar'$",
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites errors="1.0"/>
""",
        ValueError,
        r"^Cannot parse integer '1\.0': invalid literal for int\(\) with base 10: '1\.0'$",
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites>
  <testsuite/>
</testsuites>
""",
        ValueError,
        "^Attribute 'name' for <testsuite> is required, but not present$",
    ),
    (
        r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world" timestamp="2026-01-14T23:59:58+00:00" disabled="15" errors="3" failures="1" skipped="2" tests="2" assertions="2" time="32.000">
  <testsuite name="test suite one" timestamp="2026-01-14T23:59:59+00:00" disabled="15" errors="3" failures="1" skipped="2" tests="2" assertions="2" time="32.000">
    <testcase name="test case two" disabled="15" errors="3" failures="1" skipped="2" tests="1" time="17.000">
      <skipped type="skipped">
        <foo/>
      </skipped>
      <failure type="failure">
        <foo/>
      </failure>
    </testcase>
  </testsuite>
</testsuites>
""",
        ValueError,
        "^Only char data accepted in <failure>$",
    ),
]


@pytest.mark.parametrize(
    "content, expected_exception, expected_match", DESERIALIZATION_FAIL_TEST_CASES
)
def test_deserialization_fail(
    content: str, expected_exception: type[BaseException], expected_match: str
) -> None:
    with pytest.raises(expected_exception, match=expected_match):
        _Parser().parse(content.encode("utf-8"))


def test_parse_junit_xml(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_junit_xml(tmp_path / "does-not-exist")

    file = tmp_path / "file.xml"
    file.write_text("""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="hello world"/>""")
    assert parse_junit_xml(file) == JUnitXML(
        timestamp=None,
        name="hello world",
        stats=Stats(),
        testsuites=[],
    )

    file.write_text("""<?xml version="1.1" encoding="utf-8"?>""")
    with pytest.raises(
        ValueError, match="^JUnit XML file must contain <testsuites> element$"
    ):
        parse_junit_xml(file)

    file.write_text("""<testsuites><bar</testsuites>""")
    with pytest.raises(ValueError, match=".*file.xml: [nN]ot well-formed"):
        parse_junit_xml(file)
