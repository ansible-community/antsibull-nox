# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Error reporting.
"""

from __future__ import annotations

import nox

from ..messages import Level, Message


def print_messages(
    *, session: nox.Session, messages: list[Message], fail_msg: str
) -> None:
    """
    Print messages, and error out if at least one error has been found.
    """
    found_error = False
    for message in sorted(messages):
        loc_line = "0"
        loc_column = 0
        if message.position is not None:
            loc_line = str(message.position.line)
            loc_column = message.position.column or 0
            if not message.position.exact:
                loc_line = f"~{loc_line}"
        prefix = f"{message.file or ''}:{loc_line}:{loc_column}:"
        if message.id is not None:
            prefix = f"{prefix} [{message.id}]"
        content = message.message
        if message.symbol is not None:
            content = f"{content} [{message.symbol}]"
        if message.hint is not None:
            content = f"{content}\n{message.hint}"
        if message.note is not None:
            content = f"{content}\nNote: {message.note}"
        first = True
        for line in content.splitlines():
            print(f"{prefix} {line}")
            if first:
                first = False
                prefix = " " * len(prefix)
        if message.level in (Level.WARNING, Level.ERROR):
            found_error = True
    if found_error:
        session.error(fail_msg)
