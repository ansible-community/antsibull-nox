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
from pathlib import Path

from ..data.antsibull_nox_data_util import Level as _DataLevel
from ..data.antsibull_nox_data_util import Location as _DataLocation
from ..data.antsibull_nox_data_util import Message as _DataMessage
from . import Level, Location, Message
from .utils import find_json as _find_json


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
    if data["messages"]:
        for message in data["messages"]:
            path = os.path.relpath(message["absolutePath"], source_path)
            messages.append(
                Message(
                    file=path,
                    position=Location(line=message["line"], column=message["column"]),
                    end_position=None,
                    level=Level.ERROR,
                    id=message["messageId"],
                    symbol=message["symbol"],
                    message=message["message"],
                )
            )
    return messages


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

    messages = []
    for message in data:
        path = os.path.relpath(message["filename"], source_path)
        hint: str | None = None
        if message.get("fix"):
            fix = message["fix"]
            if "message" in fix:
                hint = fix["message"]
        messages.append(
            Message(
                file=path,
                position=Location(
                    line=message["location"]["row"],
                    column=message["location"]["column"],
                ),
                end_position=Location(
                    line=message["end_location"]["row"],
                    column=message["end_location"]["column"],
                ),
                level=Level.ERROR,
                id=message["code"],
                message=message["message"],
                hint=hint,
                url=message["url"],
            )
        )
    return messages


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
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            path = os.path.relpath(
                root_path / data["file"],
                source_path,
            )
            level = _mypy_severity.get(data["severity"], Level.ERROR)
            messages.append(
                Message(
                    file=path,
                    position=Location(
                        line=data["line"],
                        column=data["column"],
                    ),
                    end_position=None,
                    level=level,
                    id=data["code"],
                    message=data["message"],
                    hint=data["hint"],
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
        return Location(line=data.line, column=data.column)

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


def parse_antsibull_docs_errors(
    *,
    output: str,
) -> list[Message]:
    """
    Parse errors reported by antsibull-docs lint-collection-docs 'json' format.
    """
    try:
        data = json.loads(_find_json(output))
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
    for message in data["messages"]:
        messages.append(
            Message(
                file=message["path"],
                position=(
                    Location(
                        line=message["row"],
                        column=message.get("column"),
                    )
                    if message.get("row") is not None
                    else None
                ),
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=message["message"],
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
