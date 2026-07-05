# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
JUnit XML parsing support.
"""

from __future__ import annotations

import abc
import dataclasses
import datetime
import enum
import xml.parsers.expat
from pathlib import Path

from ._junit import Error, Failure, Skipped, Stats, Testcase, Testsuite


@dataclasses.dataclass
class JUnitXML:
    """
    Content of a parsed JUnit XML file.
    """

    timestamp: datetime.datetime | None
    name: str | None
    stats: Stats
    testsuites: list[Testsuite]


class _Result(enum.Enum):
    """
    Action for the parser when closing an element.
    """

    RETURN = 1
    DONE = 2


def _required(tag: str, attrs: dict[str, str], attr: str) -> str:
    value = attrs.get(attr)
    if value is None:
        raise ValueError(f"Attribute {attr!r} for <{tag}> is required, but not present")
    return value


def _parse_timestamp(timestamp: str | None) -> datetime.datetime | None:
    if timestamp is None:
        return None
    try:
        value = datetime.datetime.fromisoformat(timestamp)
    except Exception as exc:
        raise ValueError(f"Cannot parse time stamp {timestamp!r}: {exc}") from exc
    return value.astimezone(tz=datetime.timezone.utc)


def _parse_timedelta(value: str | None) -> datetime.timedelta | None:
    if value is None:
        return None
    try:
        return datetime.timedelta(seconds=float(value))
    except Exception as exc:
        raise ValueError(f"Cannot parse time delta {value!r}: {exc}") from exc


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception as exc:
        raise ValueError(f"Cannot parse integer {value!r}: {exc}") from exc


def _parse_stats(attrs: dict[str, str]) -> Stats:
    return Stats(
        disabled=_parse_int(attrs.get("disabled")),
        errors=_parse_int(attrs.get("errors")),
        failures=_parse_int(attrs.get("failures")),
        skipped=_parse_int(attrs.get("skipped")),
        tests=_parse_int(attrs.get("tests")),
        assertions=_parse_int(attrs.get("assertions")),
        time=_parse_timedelta(attrs.get("time")),
    )


class _ParserBase(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def start_element(self, name: str, attrs: dict[str, str]) -> _ParserBase | None:
        """
        Return a subparser to process the element instead.
        """

    @abc.abstractmethod
    def end_element(self, name: str) -> _Result | None:
        """
        When returning ``_Result.RETURN``, returns to the previous parser.
        """

    @abc.abstractmethod
    def char_data(self, data: str) -> None:
        """
        Accept char data.
        """

    @abc.abstractmethod
    def returned(self, subparser: _ParserBase) -> None:
        """
        Called when a subparser returns.
        """


class _ElementParser(_ParserBase, metaclass=abc.ABCMeta):
    def __init__(self, name: str) -> None:
        self.name = name

    def end_element(self, name: str) -> _Result | None:
        if self.name != name:  # pragma: no cover
            raise AssertionError(
                f"Internal error: expected {self.name!r}, got {name!r}"
            )
        return _Result.RETURN


class _IgnoreParser(_ElementParser):
    def start_element(self, name: str, attrs: dict[str, str]) -> _ParserBase | None:
        return _IgnoreParser(name)

    def char_data(self, data: str) -> None:
        pass

    def returned(self, subparser: _ParserBase) -> None:
        pass


class _StringContentParser(_ElementParser):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.content: list[str] = []

    def get_content(self) -> str:
        """
        Return parsed char data content.
        """
        return "".join(self.content)

    def start_element(self, name: str, attrs: dict[str, str]) -> _ParserBase | None:
        raise ValueError(f"Only char data accepted in <{self.name}>")

    def char_data(self, data: str) -> None:
        self.content.append(data)

    def returned(self, subparser: _ParserBase) -> None:
        pass  # pragma: no cover


class _SkippedParser(_ElementParser):
    def __init__(self, attrs: dict[str, str]) -> None:
        super().__init__("skipped")
        self.message = attrs.get("message")
        self.type = attrs.get("type")

    def get_result(self) -> Skipped:
        """
        Return parsed Skipped.
        """
        return Skipped(message=self.message)

    def start_element(self, name: str, attrs: dict[str, str]) -> _ParserBase | None:
        return _IgnoreParser(name)

    def char_data(self, data: str) -> None:
        pass

    def returned(self, subparser: _ParserBase) -> None:
        pass


class _FailureParser(_StringContentParser):
    def __init__(self, attrs: dict[str, str]) -> None:
        super().__init__("failure")
        self.message = attrs.get("message")
        self.type = attrs.get("type")
        self.content: list[str] = []

    def get_result(self) -> Failure:
        """
        Return parsed Failure.
        """
        return Failure(
            message=self.message,
            type=self.type,
            description=self.get_content() or None,
        )


class _ErrorParser(_StringContentParser):
    def __init__(self, attrs: dict[str, str]) -> None:
        super().__init__("error")
        self.message = attrs.get("message")
        self.type = attrs.get("type")
        self.content: list[str] = []

    def get_result(self) -> Error:
        """
        Return parsed Error.
        """
        return Error(
            message=self.message,
            type=self.type,
            description=self.get_content() or None,
        )


class _TestcaseParser(_ElementParser):
    def __init__(self, attrs: dict[str, str]) -> None:
        super().__init__("testcase")
        self.case_name = _required("testcase", attrs, "name")
        self.classname = attrs.get("classname")
        self.stats = _parse_stats(attrs)
        self.failure: Failure | None = None
        self.error: Error | None = None
        self.skipped: Skipped | None = None
        self.stdout: str | None = None
        self.stderr: str | None = None

    def get_result(self) -> Testcase:
        """
        Return parsed Testcase.
        """
        return Testcase(
            name=self.case_name,
            classname=self.classname,
            stats=self.stats,
            failure=self.failure,
            error=self.error,
            skipped=self.skipped,
            stdout=self.stdout,
            stderr=self.stderr,
        )

    def start_element(self, name: str, attrs: dict[str, str]) -> _ParserBase | None:
        if name in ("system-out", "system-err"):
            return _StringContentParser(name)
        if name == "skipped":
            return _SkippedParser(attrs)
        if name == "failure":
            return _FailureParser(attrs)
        if name == "error":
            return _ErrorParser(attrs)
        return _IgnoreParser(name)

    def char_data(self, data: str) -> None:
        pass

    def returned(self, subparser: _ParserBase) -> None:
        if isinstance(subparser, _StringContentParser):
            if subparser.name == "system-out":
                self.stdout = subparser.get_content()
            if subparser.name == "system-err":
                self.stderr = subparser.get_content()
        if isinstance(subparser, _SkippedParser):
            self.skipped = subparser.get_result()
        if isinstance(subparser, _FailureParser):
            self.failure = subparser.get_result()
        if isinstance(subparser, _ErrorParser):
            self.error = subparser.get_result()


class _TestsuiteParser(_ElementParser):
    def __init__(self, attrs: dict[str, str]) -> None:
        super().__init__("testsuite")
        self.suite_name = _required("testsuite", attrs, "name")
        self.children: list[Testsuite | Testcase] = []
        self.timestamp = _parse_timestamp(attrs.get("timestamp"))
        self.url = attrs.get("url")

    def get_result(self) -> Testsuite:
        """
        Return parsed Testsuite.
        """
        return Testsuite(
            name=self.suite_name,
            children=self.children,
            timestamp=self.timestamp,
            url=self.url,
        )

    def start_element(self, name: str, attrs: dict[str, str]) -> _ParserBase | None:
        if name == "testsuite":
            return _TestsuiteParser(attrs)
        if name == "testcase":
            return _TestcaseParser(attrs)
        return _IgnoreParser(name)

    def char_data(self, data: str) -> None:
        pass

    def returned(self, subparser: _ParserBase) -> None:
        if isinstance(subparser, (_TestsuiteParser, _TestcaseParser)):
            self.children.append(subparser.get_result())


class _TestsuitesParser(_ElementParser):
    def __init__(self) -> None:
        super().__init__("testsuites")
        self.timestamp: datetime.datetime | None = None
        self.suites_name: str | None = None
        self.stats: Stats = Stats()
        self.testsuites: list[Testsuite] = []
        self.first = True

    def start_element(self, name: str, attrs: dict[str, str]) -> _ParserBase | None:
        if self.first:
            if name != self.name:
                raise ValueError("JUnit XML file must have outer <testsuites> tag")
            self.suites_name = attrs.get("name")
            self.timestamp = _parse_timestamp(attrs.get("timestamp"))
            self.stats = _parse_stats(attrs)
            self.first = False
            return None
        if name == "testsuite":
            return _TestsuiteParser(attrs)
        return _IgnoreParser(name)

    def end_element(self, name: str) -> _Result | None:
        super().end_element(name)
        return _Result.DONE

    def char_data(self, data: str) -> None:
        pass

    def returned(self, subparser: _ParserBase) -> None:
        if isinstance(subparser, _TestsuiteParser):
            self.testsuites.append(subparser.get_result())


class _Parser:
    def __init__(self) -> None:
        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.StartElementHandler = self._start_element
        self.parser.EndElementHandler = self._end_element
        self.parser.CharacterDataHandler = self._char_data
        self.root_parser = _TestsuitesParser()
        self.parser_stack: list[_ParserBase] = [self.root_parser]
        self.found = False

    def _start_element(self, name: str, attrs: dict[str, str]) -> None:
        if not self.parser_stack:  # pragma: no cover
            raise AssertionError("Internal error: should be done")
        self.found = True
        subparser = self.parser_stack[-1].start_element(name, attrs)
        if subparser is not None:
            self.parser_stack.append(subparser)

    def _end_element(self, name: str) -> None:
        if not self.parser_stack:  # pragma: no cover
            raise AssertionError("Internal error: should be done")
        result = self.parser_stack[-1].end_element(name)
        if result == _Result.RETURN:
            return_parser = self.parser_stack.pop()
            if not self.parser_stack:  # pragma: no cover
                raise AssertionError("Internal error: returning to empty stack")
            self.parser_stack[-1].returned(return_parser)
        if result == _Result.DONE:
            return_parser = self.parser_stack.pop()

    def _char_data(self, data: str) -> None:
        if not self.parser_stack:  # pragma: no cover
            raise AssertionError("Internal error: should be done")
        self.parser_stack[-1].char_data(data)

    def parse(self, content: bytes) -> JUnitXML:
        """
        Parse the given JUnit XML file content.
        """
        self.parser.Parse(content)
        result = JUnitXML(
            timestamp=self.root_parser.timestamp,
            name=self.root_parser.suites_name,
            stats=self.root_parser.stats,
            testsuites=self.root_parser.testsuites,
        )
        if not self.found:
            raise ValueError("JUnit XML file must contain <testsuites> element")
        if self.parser_stack:  # pragma: no cover
            raise AssertionError("Internal error: should be done")
        return result


def parse_junit_xml(file: Path) -> JUnitXML:
    """
    Parse the
    """
    content = file.read_bytes()
    try:
        return _Parser().parse(content)
    except xml.parsers.expat.ExpatError as exc:
        raise ValueError(f"Error while parsing {file}: {exc}") from exc


__all__ = ("parse_junit_xml",)
