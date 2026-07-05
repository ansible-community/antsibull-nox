# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from nox.command import CommandFailed
from nox.sessions import Session

from antsibull_nox.messages import Level, Message
from antsibull_nox.reporting import (
    _BOT_DIRECTORY_ENV_VAR,
    _JUNIT_XML_PATH_ENV_VAR,
    BaseReporter,
    PartReporter,
    ProgramRun,
    Reporter,
    SessionReporter,
    Status,
    _combine_errors,
    _get_message,
    _get_status_from_exception,
    _is_test_failure,
)
from antsibull_nox.utils._junit import (
    Error,
    Failure,
    Skipped,
    Stats,
    Testcase,
    Testsuite,
)

from .utils import set_environ


def test_session_skip_error_import() -> None:
    """
    antsibull_nox.reporting assumes that an internal exception
    nox.sessions._SessionSkip is used when Session.skip() is called,
    and that an internal exception nox.sessions._SessionQuit is used
    when Session.error() is called (directly or indirectly).
    """
    # We import this locally in the function to avoid a global failure
    # if _SessionSkip and/or _SessionQuit is removed / renamed.
    from nox.sessions import _SessionQuit, _SessionSkip

    assert issubclass(_SessionSkip, Exception)
    assert issubclass(_SessionQuit, Exception)

    # Note that None is not a valid value for runner, but since neither
    # __init__() nor skip() use it, it's fine for this test.
    session = Session(runner=None)  # type: ignore[arg-type]
    with pytest.raises(_SessionSkip):
        session.skip()
    with pytest.raises(_SessionQuit):
        session.error("foo")


def test__get_status_from_exception() -> None:
    # We import this locally in the function to avoid a global failure
    # if _SessionSkip is removed / renamed.
    from nox.sessions import _SessionSkip

    assert _get_status_from_exception(None) == Status.SUCCESS
    assert _get_status_from_exception(_SessionSkip()) == Status.SKIPPED
    assert _get_status_from_exception(KeyboardInterrupt()) == Status.ABORTED
    assert _get_status_from_exception(ValueError()) == Status.FAILED


def test__is_test_failure() -> None:
    # We import this locally in the function to avoid a global failure
    # if _SessionSkip and/or _SessionQuit is removed / renamed.
    from nox.sessions import _SessionQuit, _SessionSkip

    assert _is_test_failure(None) is False
    assert _is_test_failure(_SessionSkip()) is False
    assert _is_test_failure(KeyboardInterrupt()) is False
    assert _is_test_failure(RuntimeError()) is False
    assert _is_test_failure(Exception()) is False
    assert _is_test_failure(ValueError()) is False

    assert _is_test_failure(_SessionQuit()) is True
    assert _is_test_failure(CommandFailed()) is True


def test__get_message() -> None:
    # We import this locally in the function to avoid a global failure
    # if _SessionQuit is removed / renamed.
    from nox.sessions import _SessionQuit

    assert _get_message(ValueError("foo")) is None
    assert _get_message(Exception("foo")) is None
    assert _get_message(RuntimeError("foo")) is None
    assert _get_message(_SessionQuit("foo")) == "foo"
    assert _get_message(_SessionQuit()) == ""
    assert _get_message(CommandFailed("foo")) == "foo"


def test__combine_errors() -> None:
    # We import this locally in the function to avoid a global failure
    # if _SessionQuit is removed / renamed.
    from nox.sessions import _SessionQuit

    with pytest.raises(AssertionError):
        _combine_errors([])

    exc1 = Exception("exc1")
    cf1 = CommandFailed("cf1")
    cf2 = CommandFailed("cf2")
    sq1 = _SessionQuit("sq1")
    sq2 = _SessionQuit("sq2")
    sq3 = _SessionQuit()

    # A single exception is always returned
    assert _combine_errors([exc1]) is exc1
    assert _combine_errors([cf1]) is cf1
    assert _combine_errors([sq1]) is sq1

    # Having a non-supported exception always gives the first
    assert _combine_errors([exc1, cf1, sq1]) is exc1
    assert _combine_errors([cf1, sq1, exc1]) is cf1
    assert _combine_errors([sq1, exc1, cf1]) is sq1

    # Multiple exceptions are combined
    cf1sq1 = _combine_errors([cf1, sq1])
    assert isinstance(cf1sq1, _SessionQuit)
    assert str(cf1sq1) == "cf1; sq1"

    cf12 = _combine_errors([cf1, cf2])
    assert isinstance(cf12, CommandFailed)
    assert cf12.reason == "cf1; cf2"

    sq12 = _combine_errors([sq1, sq2])
    assert isinstance(sq12, _SessionQuit)
    assert str(sq12) == "sq1; sq2"

    sq132 = _combine_errors([sq1, sq3, sq2])
    assert isinstance(sq132, _SessionQuit)
    assert str(sq132) == "sq1; (unknown); sq2"


TEST_PROGRAM_RUN_DATA: list[tuple[ProgramRun, str]] = [
    (
        ProgramRun(
            success=True,
            command=["foo", "bar baz"],
            stdout=None,
            stderr=None,
            exit_code=None,
        ),
        "$ foo 'bar baz'",
    ),
    (
        ProgramRun(
            success=True,
            command=["foo", "bar baz"],
            stdout=None,
            stderr=None,
            exit_code=1,
        ),
        "$ foo 'bar baz'",
    ),
    (
        ProgramRun(
            success=True,
            command=["foo", "bar baz"],
            stdout="a\nb",
            stderr=None,
            exit_code=None,
        ),
        "$ foo 'bar baz'\na\nb",
    ),
    (
        ProgramRun(
            success=True,
            command=["foo", "bar baz"],
            stdout=None,
            stderr="c\nd",
            exit_code=None,
        ),
        "$ foo 'bar baz'\nc\nd",
    ),
    (
        ProgramRun(
            success=True,
            command=["foo", "bar baz"],
            stdout="a\nb",
            stderr="c\nd",
            exit_code=None,
        ),
        "$ foo 'bar baz'\nc\nd\na\nb",
    ),
]


@pytest.mark.parametrize("program_run, expected_output", TEST_PROGRAM_RUN_DATA)
def test_ProgramRun(program_run: ProgramRun, expected_output: str) -> None:
    assert program_run.output == expected_output


def test_BaseReporter() -> None:
    class MyReporter(BaseReporter):
        pass

    # Single run with no error

    r = MyReporter(title="foo")
    assert r.timestamp.tzinfo is datetime.timezone.utc
    assert r.title == "foo"

    with pytest.raises(RuntimeError):
        r._assert_active()

    with pytest.raises(AssertionError):
        r.__exit__(None, None, None)

    assert r._open is False
    assert r.status == Status.SUCCESS
    assert r.effective_status == Status.SUCCESS
    assert r._start is None
    assert r._end is None
    assert r._duration is None
    assert r.active is False

    with r:
        assert r._open is True
        assert r.status == Status.SUCCESS
        assert r.effective_status == Status.SUCCESS
        assert r._start is not None
        assert r._start >= r.timestamp
        assert r._end is None
        assert r._duration is None
        assert r.active is True
        r._assert_active()

        with pytest.raises(RuntimeError):
            r.__enter__()

    assert r._open is False
    assert r.status == Status.SUCCESS
    assert r.effective_status == Status.SUCCESS
    assert r._start is not None
    assert r._end is not None
    assert r._duration == r._end - r._start
    assert r.active is False
    assert r.is_empty
    assert r._get_output() == (
        "",
        "",
        "",
        "",
    )
    assert r._get_bot_report() == []
    testcase = r._get_junit_testcase()
    assert testcase == Testcase(
        name="foo", stats=Stats(tests=1, time=testcase.stats.time)
    )

    with pytest.raises(RuntimeError):
        r.__enter__()

    # Single run with interruption (Ctrl+C)

    r = MyReporter(title="foo")
    with pytest.raises(KeyboardInterrupt):
        with r:
            assert r.status == Status.SUCCESS
            assert r.effective_status == Status.SUCCESS
            raise KeyboardInterrupt()

    assert r._open is False
    assert r.status == Status.ABORTED
    assert r.effective_status == Status.ABORTED
    assert r._start is not None
    assert r._end is not None
    assert r._duration == r._end - r._start
    assert r.active is False
    assert r.is_empty
    assert r._get_output() == (
        "",
        "",
        "",
        "",
    )
    assert r._get_bot_report() == [
        {
            "message": "Failures in nox `foo`.",
            "output": "Please see the CI output for details.",
        },
    ]
    testcase = r._get_junit_testcase()
    assert testcase == Testcase(
        name="foo",
        stats=Stats(tests=1, errors=1, time=testcase.stats.time),
        error=Error("The test case was forcefully aborted", type="aborted"),
    )

    # Single run with error due to exception

    r = MyReporter(title="foo")
    with pytest.raises(ValueError, match="^simulated error in test$"):
        with r:
            assert r.status == Status.SUCCESS
            assert r.effective_status == Status.SUCCESS
            raise ValueError("simulated error in test")

    assert r._open is False
    assert r.status == Status.FAILED
    assert r.effective_status == Status.FAILED
    assert r._start is not None
    assert r._end is not None
    assert r._duration == r._end - r._start
    assert r.active is False
    assert r.is_empty

    # Single run with warning message

    r = MyReporter(title="foo")
    with r:
        assert r._status == Status.SUCCESS
        assert r.effective_status == Status.SUCCESS
        r.report_messages(
            [
                Message(
                    file="foo/bar.baz",
                    position=None,
                    end_position=None,
                    level=Level.WARNING,
                    id=None,
                    message="A warning",
                ),
            ]
        )
        assert r._status == Status.SUCCESS
        assert r.effective_status == Status.SUCCESS

    assert r._open is False
    assert r.status == Status.SUCCESS
    assert r.effective_status == Status.SUCCESS
    assert r._start is not None
    assert r._end is not None
    assert r._duration == r._end - r._start
    assert r.active is False
    assert not r.is_empty
    assert r._get_output() == (
        "",
        "",
        "foo/bar.baz:0:0: A warning",
        "foo/bar.baz:0:0: A warning",
    )
    assert r._get_bot_report() == []
    testcase = r._get_junit_testcase()
    assert testcase == Testcase(
        name="foo",
        stats=Stats(tests=1, time=testcase.stats.time),
        stdout="foo/bar.baz:0:0: A warning",
    )

    # Single run with error due to messages

    r = MyReporter(title="foo")
    with r:
        assert r._status == Status.SUCCESS
        assert r.effective_status == Status.SUCCESS
        r.report_messages(
            [
                Message(
                    file="foo/bar.baz",
                    position=None,
                    end_position=None,
                    level=Level.ERROR,
                    id=None,
                    message="An error",
                ),
            ]
        )
        assert r._status == Status.SUCCESS
        assert r.effective_status == Status.FAILED

    assert r._open is False
    assert r.status == Status.SUCCESS
    assert r.effective_status == Status.FAILED
    assert r._start is not None
    assert r._end is not None
    assert r._duration == r._end - r._start
    assert r.active is False
    assert not r.is_empty
    assert r._get_output() == (
        "",
        "",
        "foo/bar.baz:0:0: An error",
        "foo/bar.baz:0:0: An error",
    )
    assert r._get_bot_report() == [
        {
            "message": "Failures in nox `foo`:",
            "output": "foo/bar.baz:0:0: An error",
        },
    ]
    testcase = r._get_junit_testcase()
    assert testcase == Testcase(
        name="foo",
        stats=Stats(tests=1, failures=1, time=testcase.stats.time),
        failure=Failure(None, description="foo/bar.baz:0:0: An error"),
    )

    # Single run with error due failed program run (and one successful run)

    r = MyReporter(title="foo")
    with r:
        assert r._status == Status.SUCCESS
        assert r.effective_status == Status.SUCCESS
        r._program_runs.append(
            ProgramRun(
                success=True,
                command=["baz", "bam bar"],
                stdout="asdf",
                stderr=None,
                exit_code=0,
            )
        )
        assert r._status == Status.SUCCESS
        assert r.effective_status == Status.SUCCESS
        r.add_failure_output(
            command=["foo", "bar"],
            stdout=None,
            stderr=None,
            exit_code=1,
        )
        assert r._status == Status.SUCCESS
        assert r.effective_status == Status.FAILED

    assert r.status == Status.SUCCESS
    assert r.effective_status == Status.FAILED
    assert r._get_output() == (
        "asdf",
        "",
        "",
        "$ foo bar",
    )
    assert r._get_bot_report() == [
        {
            "message": "Failures in nox `foo`:",
            "output": "$ foo bar",
        },
    ]
    testcase = r._get_junit_testcase()
    assert testcase == Testcase(
        name="foo",
        stats=Stats(tests=1, failures=1, time=testcase.stats.time),
        failure=Failure(None, description="$ foo bar"),
    )

    # Single run with error due to messages and a failed program run

    r = MyReporter(title="foo")
    with r:
        r.report_messages(
            [
                Message(
                    file="foo/bar.baz",
                    position=None,
                    end_position=None,
                    level=Level.ERROR,
                    id=None,
                    message="An error",
                ),
            ]
        )
        r.add_failure_output(
            command=["foo", "bar"],
            stdout="stdout",
            stderr="stderr",
            exit_code=1,
        )

    assert r.status == Status.SUCCESS
    assert r.effective_status == Status.FAILED
    assert r._get_output() == (
        "stdout",
        "stderr",
        "foo/bar.baz:0:0: An error",
        "foo/bar.baz:0:0: An error\n\n$ foo bar\nstderr\nstdout",
    )
    assert r._get_bot_report() == [
        {
            "message": "Failures in nox `foo`:",
            "output": "foo/bar.baz:0:0: An error\n" "\n" "$ foo bar\nstderr\nstdout",
        },
    ]
    testcase = r._get_junit_testcase()
    assert testcase == Testcase(
        name="foo",
        stats=Stats(tests=1, failures=1, time=testcase.stats.time),
        failure=Failure(
            None, description="foo/bar.baz:0:0: An error\n\n$ foo bar\nstderr\nstdout"
        ),
    )

    # Single run with skipped part

    # We import this locally in the function to avoid a global failure
    # if _SessionSkip is removed / renamed.
    from nox.sessions import _SessionSkip

    r = MyReporter(title="foo")
    with pytest.raises(_SessionSkip):
        with r:
            raise _SessionSkip()

    assert r.status == Status.SKIPPED
    assert r.effective_status == Status.SKIPPED
    assert r._get_output() == (
        "",
        "",
        "",
        "",
    )
    assert r._get_bot_report() == []
    testcase = r._get_junit_testcase()
    assert testcase == Testcase(
        name="foo",
        stats=Stats(tests=1, skipped=1, time=testcase.stats.time),
        skipped=Skipped(None),
    )


class FakeNoxSession:
    def __init__(self, name: str) -> None:
        self.name = name


def test_PartReporter() -> None:
    reporter = Reporter()
    nox_session = FakeNoxSession("foo session")
    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )

    part_reporter = PartReporter(owner=session_reporter, title="bar part")
    assert session_reporter.current_part is None
    with part_reporter:
        assert session_reporter.current_part is part_reporter
    assert session_reporter.current_part is None

    part_reporter = PartReporter(owner=session_reporter, title="bar part")
    with pytest.raises(CommandFailed):
        with part_reporter:
            raise CommandFailed("foo")
    assert session_reporter.current_part is None

    part_reporter = PartReporter(
        owner=session_reporter, title="bar part", continue_on_error=True
    )
    assert len(session_reporter._collected_errors) == 0
    with part_reporter:
        exception = CommandFailed("foo")
        raise exception
    assert session_reporter.current_part is None
    assert len(session_reporter._collected_errors) == 1
    assert session_reporter._collected_errors[0] is exception


def test_SessionReporter() -> None:
    reporter = Reporter()
    nox_session = FakeNoxSession("foo session")

    # No part

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with session_reporter:
        assert session_reporter.current_part is None

    assert session_reporter._get_bot_report_file() is None
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[],
    )

    # One part with continue_on_error == True, but exception

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    session_reporter.__enter__()
    assert session_reporter.current_part is None
    with session_reporter.get_part_reporter(
        "foo part", continue_on_error=True
    ) as part_reporter:
        assert part_reporter.title == "foo part"
        assert session_reporter.current_part is part_reporter
        raise CommandFailed("foo bar")
    assert session_reporter.current_part is None
    with pytest.raises(CommandFailed, match="^foo bar$"):
        session_reporter.__exit__(None, None, None)

    assert session_reporter._get_bot_report_file() == {
        "verified": True,
        "docs": "",
        "results": [
            {
                "message": "Failures in nox session `foo session`, part `foo part`.",
                "output": "Please see the CI output for details.",
            }
        ],
    }
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session/foo part",
                stats=Stats(
                    failures=1,
                    tests=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
                failure=Failure(
                    message=None,
                    description="Please see the CI output for details.",
                ),
            ),
        ],
    )

    # Two parts

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with session_reporter:
        assert session_reporter.current_part is None
        with session_reporter.get_part_reporter("foo part") as part_reporter:
            assert part_reporter.title == "foo part"
            assert session_reporter.current_part is part_reporter
        assert session_reporter.current_part is None
        with pytest.raises(ValueError, match="^meh$"):
            with session_reporter.get_part_reporter("bar part") as part_reporter:
                assert part_reporter.title == "bar part"
                assert session_reporter.current_part is part_reporter
                raise ValueError("meh")
        assert session_reporter.current_part is None

    assert session_reporter._get_bot_report_file() == {
        "docs": "",
        "results": [
            {
                "message": "Failures in nox session `foo session`, part `bar part`.",
                "output": "Please see the CI output for details.",
            },
        ],
        "verified": True,
    }
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session/foo part",
                stats=Stats(
                    tests=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
            ),
            Testcase(
                name="foo session/bar part",
                stats=Stats(
                    failures=1,
                    tests=1,
                    time=testsuite.children[1].stats.time,  # type: ignore[union-attr]
                ),
                failure=Failure(
                    message=None,
                    description="Please see the CI output for details.",
                ),
            ),
        ],
    )

    # Only main content with warning

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with session_reporter:
        assert session_reporter.current_part is None
        session_reporter.report_messages(
            [
                Message(
                    file="foo/bar.baz",
                    position=None,
                    end_position=None,
                    level=Level.WARNING,
                    id=None,
                    message="A warning",
                ),
            ]
        )

    assert session_reporter._get_bot_report_file() is None
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session",
                stats=Stats(
                    tests=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
                stdout="foo/bar.baz:0:0: A warning",
            ),
        ],
    )

    # Only main content with error

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with session_reporter:
        assert session_reporter.current_part is None
        session_reporter.report_messages(
            [
                Message(
                    file="foo/bar.baz",
                    position=None,
                    end_position=None,
                    level=Level.ERROR,
                    id=None,
                    message="An error",
                ),
            ]
        )

    assert session_reporter._get_bot_report_file() == {
        "docs": "",
        "results": [
            {
                "message": "Failures in nox session `foo session`:",
                "output": "foo/bar.baz:0:0: An error",
            },
        ],
        "verified": True,
    }
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session",
                stats=Stats(
                    failures=1,
                    tests=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
                failure=Failure(
                    message=None,
                    description="foo/bar.baz:0:0: An error",
                ),
            ),
        ],
    )

    # Two parts + main content

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with session_reporter:
        session_reporter.report_messages(
            [
                Message(
                    file="foo/bar.baz",
                    position=None,
                    end_position=None,
                    level=Level.ERROR,
                    id=None,
                    message="An error",
                ),
            ]
        )
        assert session_reporter.current_part is None
        with session_reporter.get_part_reporter("foo part") as part_reporter:
            assert part_reporter.title == "foo part"
            assert session_reporter.current_part is part_reporter
        assert session_reporter.current_part is None
        with pytest.raises(ValueError, match="^meh$"):
            with session_reporter.get_part_reporter("bar part") as part_reporter:
                assert part_reporter.title == "bar part"
                assert session_reporter.current_part is part_reporter
                raise ValueError("meh")
        assert session_reporter.current_part is None

    assert session_reporter._get_bot_report_file() == {
        "docs": "",
        "results": [
            {
                "message": "Failures in nox session `foo session`:",
                "output": "foo/bar.baz:0:0: An error",
            },
            {
                "message": "Failures in nox session `foo session`, part `bar part`.",
                "output": "Please see the CI output for details.",
            },
        ],
        "verified": True,
    }
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session",
                stats=Stats(
                    tests=1,
                    failures=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
                failure=Failure(
                    message=None,
                    description="foo/bar.baz:0:0: An error",
                ),
            ),
            Testcase(
                name="foo session/foo part",
                stats=Stats(
                    tests=1,
                    time=testsuite.children[1].stats.time,  # type: ignore[union-attr]
                ),
            ),
            Testcase(
                name="foo session/bar part",
                stats=Stats(
                    failures=1,
                    tests=1,
                    time=testsuite.children[2].stats.time,  # type: ignore[union-attr]
                ),
                failure=Failure(
                    message=None,
                    description="Please see the CI output for details.",
                ),
            ),
        ],
    )

    # Failure with no report

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with pytest.raises(ValueError):
        with session_reporter:
            raise ValueError()

    assert session_reporter._get_bot_report_file() == {
        "docs": "",
        "results": [
            {
                "message": "Session `foo session` failed.",
                "output": "Please see the CI output for details.",
            },
        ],
        "verified": True,
    }
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session",
                stats=Stats(
                    tests=1,
                    failures=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
                failure=Failure(
                    message=None,
                    description="Please see the CI output for details.",
                ),
            ),
        ],
    )

    # Aborted

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with pytest.raises(KeyboardInterrupt):
        with session_reporter:
            raise KeyboardInterrupt()

    assert session_reporter._get_bot_report_file() == {
        "docs": "",
        "results": [
            {
                "message": "Session `foo session` failed.",
                "output": "Please see the CI output for details.",
            },
        ],
        "verified": True,
    }
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session",
                stats=Stats(
                    tests=1,
                    errors=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
                error=Error(
                    message=None,
                    description="Please see the CI output for details.",
                ),
            ),
        ],
    )

    # Skipped

    # We import this locally in the function to avoid a global failure
    # if _SessionSkip is removed / renamed.
    from nox.sessions import _SessionSkip

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with pytest.raises(_SessionSkip):
        with session_reporter:
            raise _SessionSkip()

    assert session_reporter._get_bot_report_file() == {
        "docs": "",
        "results": [
            {
                "message": "Session `foo session` failed.",
                "output": "Please see the CI output for details.",
            },
        ],
        "verified": True,
    }
    testsuite = session_reporter._get_junit_testsuite()
    assert testsuite == Testsuite(
        name="foo session",
        timestamp=session_reporter.timestamp,
        children=[
            Testcase(
                name="foo session",
                stats=Stats(
                    tests=1,
                    skipped=1,
                    time=testsuite.children[0].stats.time,  # type: ignore[union-attr]
                ),
                skipped=Skipped(message=None),
            ),
        ],
    )

    # Active part reporter on session reporter exit

    session_reporter = SessionReporter(
        owner=reporter,
        session=nox_session,  # type: ignore[arg-type]
        url=None,
    )
    with pytest.raises(RuntimeError):
        with session_reporter:
            part_reporter = session_reporter.get_part_reporter("foo part")
            assert session_reporter.current_part is None
            part_reporter.__enter__()
            assert session_reporter.current_part is part_reporter


def test_Reporter(tmp_path: Path) -> None:
    _BOT_DIRECTORY_ENV_VAR,
    _JUNIT_XML_PATH_ENV_VAR,
    with set_environ(_BOT_DIRECTORY_ENV_VAR, None):
        with set_environ(_JUNIT_XML_PATH_ENV_VAR, None):
            with patch("atexit.register", return_value=None):
                # Lifecycle 1/2

                reporter = Reporter()

                with pytest.raises(RuntimeError, match="Reporter is not yet set up"):
                    reporter.assert_setup()

                reporter._setup()
                reporter.assert_setup()

                # Registering twice with no sessions is fine
                reporter._setup()

                write_bot_mock = MagicMock()
                write_junit_mock = MagicMock()
                with patch.object(Reporter, "_write_bot_reports", write_bot_mock):
                    with patch.object(Reporter, "_write_junit_xml", write_junit_mock):
                        reporter._shutdown()
                        write_bot_mock.assert_not_called()
                        write_junit_mock.assert_not_called()

                with pytest.raises(RuntimeError, match="shutting down"):
                    reporter.assert_setup()

                # Lifecycle 2/2

                reporter = Reporter()

                with pytest.raises(RuntimeError, match="Reporter is not yet set up"):
                    reporter.assert_setup()

                reporter._setup()
                reporter.assert_setup()

                nox_session = FakeNoxSession("foo")
                assert reporter.timestamp is None
                session_reporter_1 = reporter.get_session_reporter(
                    session=nox_session,  # type: ignore[arg-type]
                )
                assert reporter.timestamp == session_reporter_1.timestamp
                session_reporter_1.timestamp = datetime.datetime(
                    2026,
                    1,
                    15,
                    13,
                    14,
                    16,
                    microsecond=312341,
                    tzinfo=datetime.timezone.utc,
                )
                reporter.timestamp = session_reporter_1.timestamp

                # Now we have a session
                with pytest.raises(RuntimeError, match="Reporter is already set up"):
                    reporter._setup()

                nox_session_2 = FakeNoxSession("bar")
                session_reporter_2 = reporter.get_session_reporter(
                    session=nox_session_2,  # type: ignore[arg-type]
                )
                session_reporter_2.timestamp = datetime.datetime(
                    2026,
                    1,
                    15,
                    13,
                    14,
                    18,
                    microsecond=589198,
                    tzinfo=datetime.timezone.utc,
                )

                write_bot_mock = MagicMock()
                write_junit_mock = MagicMock()
                with patch.object(Reporter, "_write_bot_reports", write_bot_mock):
                    with patch.object(Reporter, "_write_junit_xml", write_junit_mock):
                        reporter._shutdown()
                        write_bot_mock.assert_not_called()
                        write_junit_mock.assert_not_called()

                        with set_environ(_BOT_DIRECTORY_ENV_VAR, "foo"):
                            reporter._shutdown()
                        write_bot_mock.assert_called_once()
                        write_junit_mock.assert_not_called()

                        with set_environ(_JUNIT_XML_PATH_ENV_VAR, "foo"):
                            reporter._shutdown()
                        write_bot_mock.assert_called_once()
                        write_junit_mock.assert_called_once()

                with pytest.raises(RuntimeError, match="shutting down"):
                    reporter.assert_setup()

                reporter._shutdown()
                with session_reporter_2:
                    with pytest.raises(
                        RuntimeError,
                        match="SessionReporter 'bar' still active at shutdown time",
                    ):
                        reporter._shutdown()
                    session_reporter_2.report_messages(
                        [
                            Message(
                                file="foo/bar.baz",
                                position=None,
                                end_position=None,
                                level=Level.ERROR,
                                id=None,
                                message="An error",
                            ),
                        ]
                    )

                session_reporter_2._duration = datetime.timedelta(
                    seconds=42, microseconds=123456
                )

                bot_reports = reporter._get_bot_reports()
                assert bot_reports == {
                    "bar": {
                        "docs": "",
                        "results": [
                            {
                                "message": "Failures in nox session `bar`:",
                                "output": "foo/bar.baz:0:0: An error",
                            },
                        ],
                        "verified": True,
                    },
                }

                junit_xml = reporter._get_junit_xml()
                assert junit_xml == r"""<?xml version="1.1" encoding="utf-8"?>
<testsuites name="antsibull-nox" timestamp="2026-01-15T13:14:16+00:00" failures="1" tests="1" time="42.123">
  <testsuite name="foo" timestamp="2026-01-15T13:14:16+00:00"/>
  <testsuite name="bar" timestamp="2026-01-15T13:14:18+00:00" failures="1" tests="1" time="42.123">
    <testcase name="bar" failures="1" tests="1" time="42.123">
      <failure type="failure">foo/bar.baz:0:0: An error</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

                bot_dir = tmp_path / "bot"
                junit_dir = tmp_path / "junit"
                junit_file = junit_dir / "output.xml"
                assert not bot_dir.exists()
                assert not junit_dir.exists()
                assert not junit_file.exists()
                with set_environ(_BOT_DIRECTORY_ENV_VAR, str(bot_dir)):
                    with set_environ(_JUNIT_XML_PATH_ENV_VAR, str(junit_file)):
                        reporter._shutdown()
                assert bot_dir.is_dir()
                assert junit_dir.is_dir()
                assert junit_file.is_file()

                files = list(bot_dir.iterdir())
                assert len(files) == 1
                assert files[0].name == "antsibull-nox-bar.json"
                assert files[0].read_text() == (
                    """{\n"""
                    """    "docs": "", \n"""
                    """    "results": [\n"""
                    """        {\n"""
                    """            "message": "Failures in nox session `bar`:", \n"""
                    """            "output": "foo/bar.baz:0:0: An error"\n"""
                    """        }\n"""
                    """    ], \n"""
                    """    "verified": true\n"""
                    """}"""
                )

                assert junit_file.read_text() == junit_xml
