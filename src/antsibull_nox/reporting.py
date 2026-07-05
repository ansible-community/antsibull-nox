# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Reporting subsystem of antsibull-nox.
"""

from __future__ import annotations

import abc
import atexit
import contextlib
import dataclasses
import datetime
import enum
import json
import os
import shlex
import typing as t
from pathlib import Path

import nox
import nox.command
import nox.sessions

from .messages import Level, Message
from .sessions.utils.output import format_messages_plain
from .utils import _junit

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence
    from types import TracebackType

    class BotResult(t.TypedDict):
        """
        One bot result.
        """

        message: str
        output: str

    class BotFile(t.TypedDict):
        """
        One bot file.
        """

        verified: bool
        docs: str  # URL describing tests
        results: list[BotResult]


_BOT_DIRECTORY_ENV_VAR = "ANTSIBULL_NOX_OUTPUT_BOT_DIRECTORY"
_JUNIT_XML_PATH_ENV_VAR = "ANTSIBULL_NOX_OUTPUT_JUNIT_XML_PATH"


class Status(enum.Enum):
    """
    Status of part of session.
    """

    SUCCESS = 1
    FAILED = 2
    SKIPPED = 3
    ABORTED = 4


class _FakeException(Exception):
    pass


# The type of nox' internal "skip session" and "quit session" exceptions.
# That these still exist and are being used is validated in tests/unit/test_reporting.py.
_NoxSessionSkip: type = getattr(nox.sessions, "_SessionSkip", _FakeException)
_NoxSessionQuit: type = getattr(nox.sessions, "_SessionQuit", _FakeException)


def _get_status_from_exception(value: BaseException | None) -> Status:
    if value is None:
        return Status.SUCCESS
    if isinstance(value, _NoxSessionSkip):
        return Status.SKIPPED
    if isinstance(value, KeyboardInterrupt):
        return Status.ABORTED
    return Status.FAILED


def _is_test_failure(value: BaseException | None) -> bool:
    """
    Decide whether the exception is a test failure that can potentially
    be eaten and raised later.
    """
    if value is None:
        return False
    # In case the session is skipped or aborted (Ctrl+C), do not
    # do not keep going.
    if isinstance(value, (_NoxSessionSkip, KeyboardInterrupt)):
        return False
    # In case session.error() is called or session.run() fails,
    # keep going.
    if isinstance(value, (_NoxSessionQuit, nox.command.CommandFailed)):
        return True
    # Any other exception type:
    return False


@dataclasses.dataclass
class ProgramRun:
    """
    Information on a program run.
    """

    success: bool
    command: list[str]
    stdout: str | None
    stderr: str | None
    exit_code: int | None

    @property
    def output(self) -> str:
        """
        Create an output string.
        """

        parts = [
            f"$ {shlex.join(self.command)}",
            self.stderr,
            self.stdout,
        ]
        return "\n".join(part.rstrip() for part in parts if part)


def _make_timestamp() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class BaseReporter(contextlib.AbstractContextManager, metaclass=abc.ABCMeta):
    """
    Base class for a reporter that accepts messages and other information
    about a session or a part of a session.
    """

    def __init__(
        self, *, title: str, is_active: Callable[[], bool] | None = None
    ) -> None:
        self._title = title
        self._is_active = is_active
        self._open = False
        self._status = Status.SUCCESS
        self._messages: list[Message] = []
        self._program_runs: list[ProgramRun] = []
        self._start: datetime.datetime | None = None
        self._end: datetime.datetime | None = None
        self._duration: datetime.timedelta | None = None
        self.timestamp = _make_timestamp()

    def __enter__(self) -> t.Self:
        if self._open or self._end:
            raise RuntimeError(f"{type(self).__name__} used more than once")
        self._open = True
        self._start = _make_timestamp()
        return self

    def __exit__(  # type: ignore[exit-return]
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        assert self._open
        assert self._start is not None
        self._open = False
        self._status = _get_status_from_exception(value)
        self._end = _make_timestamp()
        self._duration = self._end - self._start
        return False

    @property
    def title(self) -> str:
        """
        Return title of the part.
        """
        return self._title

    @property
    def status(self) -> Status:
        """
        Return status of the part.
        """
        return self._status

    @property
    def active(self) -> bool:
        """
        Whether the part is active.
        """
        if not self._open:
            return False
        return self._is_active() if self._is_active else True

    @property
    def is_empty(self) -> bool:
        """
        Whether nothing has been logged.
        """
        return not self._messages and not self._program_runs

    def _assert_active(self) -> None:
        if not self.active:
            raise RuntimeError(f"{type(self).__name__} is currently not active")

    # Reporting infos

    def report_messages(self, messages: Sequence[Message]) -> None:
        """
        Report a set of messages.
        """
        self._assert_active()
        self._messages.extend(messages)

    def add_failure_output(
        self,
        *,
        command: list[str],
        stdout: str | None,
        stderr: str | None,
        exit_code: int | None,
    ) -> None:
        """
        Add output of a failed command.
        """
        self._program_runs.append(
            ProgramRun(
                success=False,
                command=command,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
            )
        )

    # Report generation

    @property
    def effective_status(self) -> Status:
        """
        Return the effective status, using both ``status`` and all added data.
        """
        if self.status != Status.SUCCESS:
            return self.status
        for msg in self._messages:
            if msg.level == Level.ERROR:
                return Status.FAILED
        for run in self._program_runs:
            if not run.success:
                return Status.FAILED
        return Status.SUCCESS

    def _get_output(self) -> tuple[str, str, str, str]:
        stdout = []
        stderr = []
        messages = ""
        outputs = []
        if self._messages:
            messages = "\n".join(format_messages_plain(self._messages))
            outputs.append(messages)
        for run in self._program_runs:
            if run.stdout is not None:
                stdout.append(run.stdout)
            if run.stderr is not None:
                stderr.append(run.stderr)
            if not run.success:
                outputs.append(run.output)
        return "\n".join(stdout), "\n".join(stderr), messages, "\n\n".join(outputs)

    def _get_bot_report(self, *, prefix: str = "", suffix: str = "") -> list[BotResult]:
        if self.effective_status in {Status.SUCCESS, Status.SKIPPED}:
            return []
        if self.is_empty:
            return [
                {
                    "message": f"Failures in nox {prefix}`{self.title}`{suffix}.",
                    "output": "Please see the CI output for details.",
                }
            ]
        _, __, ___, output = self._get_output()
        return [
            {
                "message": f"Failures in nox {prefix}`{self.title}`{suffix}:",
                "output": output,
            }
        ]

    def _get_junit_testcase(self, *, prefix: str | None = None) -> _junit.Testcase:
        result = _junit.Testcase(name=f"{prefix or ''}{self.title}")
        result.stats.time = self._duration
        result.stats.tests = 1
        status = self.effective_status
        stdout, stderr, messages, output = self._get_output()
        has_output = False
        if status == Status.SKIPPED:
            result.skipped = _junit.Skipped()
            result.stats.skipped = 1
        elif status == Status.FAILED:
            result.failure = _junit.Failure(
                message=None,
                description=output or "Please see the CI output for details.",
            )
            result.stats.failures = 1
            has_output = True
        elif status == Status.ABORTED:
            result.error = _junit.Error(
                message="The test case was forcefully aborted",
                type="aborted",
                description=output or None,
            )
            result.stats.errors = 1
            has_output = True
        if not has_output:
            result.stderr = stderr or None
            result.stdout = (
                "\n\n".join(part for part in [messages, stdout] if part) or None
            )
        return result


def _get_message(error: BaseException) -> str | None:
    if isinstance(error, _NoxSessionQuit):
        return str(error)
    if isinstance(error, nox.command.CommandFailed):
        return error.reason
    return None


def _combine_errors(errors: list[BaseException]) -> BaseException:
    assert len(errors) > 0
    if len(errors) > 1:
        messages = [
            (message or "(unknown)")
            for error in errors
            if (message := _get_message(error)) is not None
        ]
        if len(messages) == len(errors):
            new_message = "; ".join(messages)
            # We use _FakeException if we cannot import _SessionQuit
            if _NoxSessionQuit is not _FakeException and any(
                not isinstance(error, nox.command.CommandFailed) for error in errors
            ):
                try:
                    return _NoxSessionQuit(new_message)
                except Exception:  # pylint: disable=broad-exception-caught
                    # If for some reason the implementation of _SessionQuit
                    # changed and trying to create the instance results in
                    # some error, we call back to using CommandFailed.
                    pass  # parma: no cover
            return nox.command.CommandFailed(new_message)
    return errors[0]


class PartReporter(BaseReporter):
    """
    Reporter for a session's part.
    """

    def __init__(
        self, *, owner: SessionReporter, title: str, continue_on_error: bool = False
    ) -> None:
        super().__init__(title=title)
        self.owner = owner
        self.continue_on_error = continue_on_error
        self._error: BaseException | None = None

    def __enter__(self) -> t.Self:
        super().__enter__()
        self.owner.current_part = self
        return self

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        super().__exit__(type_, value, traceback)
        self.owner.current_part = None
        if self.continue_on_error and value is not None and _is_test_failure(value):
            # Store and then "eat" exception, so it can be re-raised
            # at the end of the session.
            self.owner._collected_errors.append(value)
            return True
        return False


class SessionReporter(BaseReporter):
    """
    Reporter for a session.

    A session can have multiple parts, and can be global.
    """

    def __init__(
        self, *, owner: Reporter, session: nox.Session, url: str | None
    ) -> None:
        super().__init__(title=session.name)
        self.owner = owner
        self.parts: list[PartReporter] = []
        self.current_part: PartReporter | None = None
        self.url = url
        self._collected_errors: list[BaseException] = []

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> t.Literal[False]:
        super().__exit__(type_, value, traceback)
        for part in self.parts:
            if part.active:
                raise RuntimeError(
                    f"PartReporter {part.title!r} still active"
                    f" at end of SessionReporter {self.title!r}"
                )
        if self._collected_errors:
            raise _combine_errors(self._collected_errors)
        return False

    def get_part_reporter(
        self, title: str, *, continue_on_error: bool = False
    ) -> PartReporter:
        """
        Given a part's title, return a part reporter for it.
        """

        part_reporter = PartReporter(
            owner=self, title=title, continue_on_error=continue_on_error
        )
        self.parts.append(part_reporter)
        return part_reporter

    def _get_bot_report_file(self, *, prefix: str = "") -> BotFile | None:
        reports = []
        suffix = f" [[details]({self.url})]" if self.url else ""
        if not self.is_empty:
            reports.extend(
                self._get_bot_report(prefix=f"{prefix}session ", suffix=suffix)
            )
        our_prefix = f"{prefix}session `{self.title}`, part "
        for part in self.parts:
            # pylint: disable-next=protected-access
            reports.extend(part._get_bot_report(prefix=our_prefix, suffix=suffix))
        if not reports:
            if self.effective_status == Status.SUCCESS:
                return None
            reports.append(
                {
                    "message": f"Session `{self.title}` failed.",
                    "output": "Please see the CI output for details.",
                }
            )
        return {
            "verified": True,
            "docs": self.url or "",
            "results": reports,
        }

    def _get_junit_testsuite(self) -> _junit.Testsuite:
        result = _junit.Testsuite(
            name=self.title,
            timestamp=self.timestamp,
            url=self.url,
        )
        first_case: _junit.Testcase | None = None
        if not self.is_empty:
            first_case = self._get_junit_testcase()
            result.children.append(first_case)
        prefix = f"{self.title}/"
        for part in self.parts:
            # pylint: disable-next=protected-access
            testcase = part._get_junit_testcase(prefix=prefix)
            result.children.append(testcase)
            if (
                first_case
                and first_case.stats.time is not None
                and testcase.stats.time is not None
            ):
                first_case.stats.time -= testcase.stats.time
        if not result.children:
            effective_status = self.effective_status
            if effective_status == Status.FAILED:
                result.children.append(
                    _junit.Testcase(
                        name=self.title,
                        stats=_junit.Stats(tests=1, failures=1, time=self._duration),
                        failure=_junit.Failure(
                            message=None,
                            description="Please see the CI output for details.",
                        ),
                    )
                )
            if effective_status == Status.ABORTED:
                result.children.append(
                    _junit.Testcase(
                        name=self.title,
                        stats=_junit.Stats(tests=1, errors=1, time=self._duration),
                        error=_junit.Error(
                            message=None,
                            description="Please see the CI output for details.",
                        ),
                    )
                )
            if effective_status == Status.SKIPPED:
                result.children.append(
                    _junit.Testcase(
                        name=self.title,
                        stats=_junit.Stats(tests=1, skipped=1, time=self._duration),
                        skipped=_junit.Skipped(message=None),
                    )
                )
        return result


class Reporter:
    """
    The global reporter object.
    """

    def __init__(self) -> None:
        self.sessions: list[SessionReporter] = []
        self._is_setup = False
        self._is_dead = False
        self.timestamp: datetime.datetime | None = None

    def _setup(self) -> None:
        if self._is_setup:
            # This is OK as long as we don't have any sessions.
            # For example, when nox is run through `python noxfile.py`
            # Reporter._setup() will be called twice.
            if not self.sessions:
                return
            raise RuntimeError("Reporter is already set up")
        atexit.register(self._shutdown)
        self._is_setup = True

    def assert_setup(self) -> None:
        """
        Ensure that the reporter was properly set up.
        """
        if not self._is_setup:
            raise RuntimeError(
                "Reporter is not yet set up. Did you call antsibull_nox.load_antsibull_nox_toml()?"
            )
        if self._is_dead:
            raise RuntimeError("The reporter is already shutting down.")

    def get_session_reporter(
        self, session: nox.Session, *, url: str | None = None
    ) -> SessionReporter:
        """
        Given a nox session, return a session reporter for it.
        """

        self.assert_setup()
        session_reporter = SessionReporter(owner=self, session=session, url=url)
        if self.timestamp is None:
            self.timestamp = session_reporter.timestamp
        self.sessions.append(session_reporter)
        return session_reporter

    @staticmethod
    def _write_test_results(output_path: Path, content: str):
        output_dir = output_path.parent
        if output_dir:  # pragma: no branch
            output_dir.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file_obj:
            file_obj.write(content)

    @staticmethod
    def _write_test_results_to_dir(
        output_dir: Path, name: str, extension: str, content: str, *, prefix: str = ""
    ):
        Reporter._write_test_results(
            output_dir / f"{prefix}antsibull-nox-{name}.{extension}", content
        )

    def _get_bot_reports(self) -> dict[str, BotFile]:
        reports = {}
        for session in self.sessions:
            # pylint: disable-next=protected-access
            file = session._get_bot_report_file()
            if file:
                reports[session.title] = file
        return reports

    def _write_bot_reports(self, output_dir: Path) -> None:
        for file, content in self._get_bot_reports().items():
            bot_content = json.dumps(
                content, sort_keys=True, indent=4, separators=(", ", ": ")
            )
            # The collection bot will only consider files with 'ansible-test-' in it,
            # and the collection AZP scripts assume that the filename starts with it.
            self._write_test_results_to_dir(
                output_dir, file, "json", bot_content, prefix="ansible-test-"
            )

    def _get_junit_xml(self) -> str:
        testsuites = []
        for session in self.sessions:
            # pylint: disable-next=protected-access
            testsuites.append(session._get_junit_testsuite())
        return _junit.serialize_junit_xml(
            testsuites,
            name="antsibull-nox",
            timestamp=self.timestamp,
            pretty_print=True,
        )

    def _write_junit_xml(self, output_path: Path) -> None:
        junit_xml_content = self._get_junit_xml()
        self._write_test_results(output_path, junit_xml_content)

    def _shutdown(self) -> None:
        self._is_dead = True
        if not self.sessions:
            # Early exit if nothing ran. This can happen because the user ran
            # `nox --list`, the user ran `python noxfile.py` (setup() will be
            # called twice), the user asked for a non-existing session, the
            # user ran a user-defined session not managed by antsibull-nox,
            # or something else happened that caused no session to be run.
            # We do not want to write the result files in that case.
            return
        for session in self.sessions:
            if session.active:
                raise RuntimeError(
                    f"SessionReporter {session.title!r} still active at shutdown time"
                )
        if bot_directory := os.environ.get(_BOT_DIRECTORY_ENV_VAR):
            print(f"Writing bot JSON output to {bot_directory}...")
            self._write_bot_reports(Path(bot_directory))
        if junit_xml_path := os.environ.get(_JUNIT_XML_PATH_ENV_VAR):
            print(f"Writing JUnit XML output to {junit_xml_path}...")
            self._write_junit_xml(Path(junit_xml_path))


# Global program-wide Reporter instance (singleton).
_REPORTER = Reporter()


def setup() -> None:
    """
    Setup reporter. Is called internally by antsibull-nox; this is **NOT** public API.
    """
    _REPORTER._setup()  # pylint: disable=protected-access


def get_reporter() -> Reporter:
    """
    Return the instance-wide ``Reporter`` instance.
    """
    _REPORTER.assert_setup()
    return _REPORTER


def get_session_reporter(
    session: nox.Session, *, url: str | None = None
) -> SessionReporter:
    """
    Return a session reporter for a specific nox session.
    """
    return get_reporter().get_session_reporter(session, url=url)


def is_writing_bot_jsons() -> bool:
    """
    Whether the reporter will write ansibullbot JSON files.
    """
    return bool(os.environ.get(_BOT_DIRECTORY_ENV_VAR))


def is_writing_junit_xml() -> bool:
    """
    Whether the reporter will write JUnit XML files.
    """
    return bool(os.environ.get(_JUNIT_XML_PATH_ENV_VAR))


__all__ = (
    "PartReporter",
    "SessionReporter",
    "Reporter",
    "get_reporter",
    "get_session_reporter",
    "is_writing_bot_jsons",
    "is_writing_junit_xml",
    "setup",
)
