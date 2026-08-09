# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Error reporting.
"""

from __future__ import annotations

import json
import os
import typing as t
from pathlib import Path

import pydantic as _p

from ..data.antsibull_nox_data_util import Level as _DataLevel
from ..data.antsibull_nox_data_util import Location as _DataLocation
from ..data.antsibull_nox_data_util import Message as _DataMessage
from . import Level, Location, Message
from .utils import find_json as _find_json


class _PylintJSON2Message(_p.BaseModel):
    # Source:
    # https://github.com/pylint-dev/pylint/blob/7f0d9a706ad6d549168bad4acb446cf5be36f2ae/pylint/reporters/json_reporter.py#L97-L110
    type: str
    message: str
    messageId: str
    symbol: str
    confidence: str
    module: str
    path: str
    absolutePath: str
    line: int
    endLine: t.Optional[int] = None
    column: int
    endColumn: t.Optional[int] = None
    obj: str


class _PylintJSON2Root(_p.BaseModel):
    messages: list[_PylintJSON2Message] = []


def parse_pylint_json2_errors(
    *,
    source_path: Path,
    output: str,
) -> list[Message]:
    """
    Parse errors reported by pylint in 'json2' format.
    """
    try:
        data = json.loads(output)
        parsed = _PylintJSON2Root.model_validate(data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse pylint output: {exc}\n{output}",
            )
        ]

    messages = []
    for message in parsed.messages or []:
        path = os.path.relpath(message.absolutePath, source_path)
        messages.append(
            Message(
                file=path,
                position=Location(line=message.line, column=message.column),
                end_position=(
                    Location(line=message.endLine, column=message.endColumn)
                    if message.endLine is not None
                    else None
                ),
                level=Level.ERROR,
                id=message.messageId,
                symbol=message.symbol,
                message=message.message,
            )
        )
    return messages


class _RuffCheckLocation(_p.BaseModel):
    column: int  # starting with 1
    row: int  # starting with 1


class _RuffCheckEdit(_p.BaseModel):
    content: str
    end_location: t.Optional[_RuffCheckLocation] = None
    location: t.Optional[_RuffCheckLocation] = None


class _RuffCheckFix(_p.BaseModel):
    applicability: t.Literal["displayonly", "unsafe", "safe"]
    edits: list[_RuffCheckEdit]
    message: t.Optional[str] = None


class _RuffCheckMessage(_p.BaseModel):
    # Source:
    # https://github.com/astral-sh/ruff/blob/24baf2cd8fd7a191625e7029d91a45a56dda9b85/crates/ruff_db/src/diagnostic/render/json.rs#L205-L251
    cell: t.Optional[int] = None  # starting with 1
    code: t.Optional[str] = None  # optional since ruff 0.15.18
    name: t.Optional[str] = None  # present since ruff 0.15.18
    severity: t.Optional[t.Literal["info", "warning", "error", "fatal"]] = (
        None  # present since ruff 0.15.7
    )
    end_location: t.Optional[_RuffCheckLocation] = None
    filename: t.Optional[str] = None
    fix: t.Optional[_RuffCheckFix] = None
    location: t.Optional[_RuffCheckLocation] = None
    message: str
    noqa_row: t.Optional[int] = None  # starting with 1
    url: t.Optional[str] = None


_RuffCheckRoot = _p.RootModel[list[_RuffCheckMessage]]


def parse_ruff_check_errors(
    *,
    source_path: Path,
    output: str,
) -> list[Message]:
    """
    Parse errors reported by ruff check in 'json' format.
    """
    try:
        data = json.loads(output)
        parsed = _RuffCheckRoot.model_validate(data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse ruff check output: {exc}\n{output}",
            )
        ]

    def process_end_location(end_loc: _RuffCheckLocation | None) -> Location | None:
        if end_loc is None:
            return None
        end_line = end_loc.row
        end_col = end_loc.column - 1
        if end_col == 0:
            end_line -= 1
            end_col = -1
        return Location(line=end_line, column=end_col)

    messages = []
    for message in parsed.root:
        path = (
            os.path.relpath(message.filename, source_path)
            if message.filename is not None
            else None
        )
        hint = message.fix.message if message.fix else None
        messages.append(
            Message(
                file=path,
                position=(
                    Location(
                        line=message.location.row,
                        column=message.location.column,
                    )
                    if message.location
                    else None
                ),
                end_position=process_end_location(message.end_location),
                level=Level.ERROR,
                id=message.code or message.name,
                message=message.message,
                hint=hint,
                url=message.url,
            )
        )
    return messages


class _MypyLine(_p.BaseModel):
    # Source:
    # https://github.com/python/mypy/blob/5bb72b788d5c031244f04f30f571f6fa199871ad/mypy/error_formatter.py#L19-L36
    file: str
    line: int
    column: int
    # Support for end_line and end_column was added in mypy 1.20.0
    end_line: t.Optional[int] = None
    end_column: t.Optional[int] = None
    message: str
    hint: t.Optional[str]
    code: t.Optional[str]
    severity: t.Literal["error", "note"]


def parse_mypy_errors(
    *,
    root_path: Path,
    source_path: Path,
    output: str,
) -> list[Message]:
    """
    Process errors reported by mypy in 'json' format.
    """
    messages = []
    _mypy_severity = {
        "error": Level.ERROR,
        "note": Level.INFO,
    }

    def plus_one_or_none(value: int | None) -> int | None:
        if value is None:
            return None
        return value + 1

    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            parsed = _MypyLine.model_validate(data)
            path = os.path.relpath(
                root_path / parsed.file,
                source_path,
            )
            level = _mypy_severity.get(parsed.severity, Level.ERROR)
            messages.append(
                Message(
                    file=path,
                    position=Location(
                        line=parsed.line,
                        column=plus_one_or_none(parsed.column),
                    ),
                    end_position=(
                        Location(
                            line=parsed.end_line,
                            column=plus_one_or_none(parsed.end_column),
                        )
                        if parsed.end_line is not None
                        else None
                    ),
                    level=level,
                    id=parsed.code,
                    message=parsed.message,
                    hint=parsed.hint,
                )
            )
        except Exception:  # pylint: disable=broad-exception-caught
            messages.append(
                Message(
                    file=None,
                    position=None,
                    end_position=None,
                    level=Level.ERROR,
                    id=None,
                    message=f"Cannot parse mypy output: {line}",
                )
            )
    return messages


def parse_bare_framework_errors(
    *,
    output: str,
) -> list[Message]:
    """
    Process errors reported by tools from data with
    antsibull_nox.data.antsibull_nox_data.util.report_result().
    """
    try:
        data = json.loads(output)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse output: {exc}\n{output}",
            )
        ]

    def loc(data: _DataLocation | None) -> Location | None:
        if data is None:
            return None
        return Location(line=data.line, column=data.column, exact=data.exact)

    levels: dict[_DataLevel, Level] = {
        "error": Level.ERROR,
        "warning": Level.WARNING,
        "info": Level.INFO,
    }

    messages = []
    for message in data["messages"]:
        msg = _DataMessage.from_json(message)
        messages.append(
            Message(
                file=msg.file,
                position=loc(msg.start),
                end_position=loc(msg.end),
                level=levels.get(msg.level, Level.ERROR),
                id=msg.id,
                message=msg.message,
                symbol=msg.id,
                hint=msg.hint,
                note=msg.note,
                url=msg.url,
            )
        )
    return messages


class _AntsibullDocsMessage(_p.BaseModel):
    # Source:
    # https://github.com/ansible-community/antsibull-docs/blob/4be209bf7f27098b5214ab31e1d75901c594e196/src/antsibull_docs/cli/doc_commands/lint_docs.py#L58-L80
    path: str
    row: t.Optional[int]
    column: t.Optional[int]
    end_column: t.Optional[int] = None  # this was added later
    message: str


class _AntsibullDocsRoot(_p.BaseModel):
    messages: list[_AntsibullDocsMessage]
    success: bool


def parse_antsibull_docs_errors(
    *,
    output: str,
) -> list[Message]:
    """
    Parse errors reported by antsibull-docs lint-collection-docs 'json' format.
    """
    try:
        data = json.loads(_find_json(output))
        parsed = _AntsibullDocsRoot.model_validate(data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=f"Cannot parse antsibull-docs lint-collection-docs output: {exc}\n{output}",
            )
        ]

    messages = []
    for message in parsed.messages:
        row = message.row
        messages.append(
            Message(
                file=message.path,
                position=(
                    Location(
                        line=row,
                        column=message.column,
                    )
                    if row is not None
                    else None
                ),
                end_position=(
                    Location(
                        line=row,
                        column=message.end_column,
                    )
                    if row is not None and message.end_column is not None
                    else None
                ),
                level=Level.ERROR,
                id=None,
                message=message.message,
            )
        )
    return messages


__all__ = (
    "parse_pylint_json2_errors",
    "parse_ruff_check_errors",
    "parse_mypy_errors",
    "parse_bare_framework_errors",
    "parse_antsibull_docs_errors",
)
