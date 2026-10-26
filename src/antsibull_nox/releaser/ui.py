# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
UI helpers.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
import time
import typing as t

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

    _T = t.TypeVar("_T")

    LogFunction = Callable[[str], None]


def log(message: str) -> None:
    """
    Emit releaser log message.
    """
    print(message)


class Retry(Exception):
    """
    Indicate that we're not done yet.
    """


def wait_for(
    action: Callable[[LogFunction], _T], *, interval: datetime.timedelta
) -> _T:
    """
    Call action until the function succeeds or raises another exception than ``Retry``.

    The action is called at most once every ``interval``.

    The action is passed a ``LogFunction`` that it can use to log output.
    """
    while True:
        start = datetime.datetime.now()
        try:
            return action(log)
        except Retry:
            done = datetime.datetime.now()
            delta = done - start
            if delta < interval:
                time.sleep((interval - delta).total_seconds())
            continue


def prompt_user(
    prompt: str,
    *,
    accept: Sequence[str],
    default: str | None = None,
    abort: str | None = None,
) -> str:
    """
    Ask user a question.
    """

    query = "/".join(accept)
    if default is not None:
        query = f"{query}, default={default}"
    prompt = f"{prompt} ({query}) "
    while True:
        try:
            value = input(prompt)
        except KeyboardInterrupt:
            if abort is not None:
                return abort
            raise
        if value in accept:
            return value
        if not value and default is not None:
            return default
        log(f"Value {value!r} is not acceptable. Try again.")


def retry(action: Callable[[], _T], *, what: str, num_retries: int = 3) -> _T:
    """
    Retry an action at most ``num_retries`` times in case of ``ValueError``s.
    """
    for index in range(num_retries):
        try:
            return action()
        except ValueError as exc:
            log(f"{what} failed with {exc}, retrying... ({index + 1}/{num_retries})")
    return action()


def _show_pager(lines: list[str]) -> None:
    env = dict(os.environ)
    env["LESS"] = "FRSX"
    with subprocess.Popen(
        ["less"], shell=False, stdin=subprocess.PIPE, stdout=sys.stdout, env=env
    ) as p:
        p.communicate(input="\n".join(lines).encode("utf-8"))


def show_lines(lines: list[str]) -> None:
    """
    Show a list of lines on the screen.
    Use a pager if possible.
    """
    if sys.stdout.isatty():
        try:
            with subprocess.Popen(
                ["less", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            ) as p:
                p.communicate()
            if p.returncode == 0:
                _show_pager(lines)
                return
        except IOError:
            pass
    for line in lines:
        log(line)


__all__ = ("Retry", "log", "prompt_user", "show_lines", "wait_for")
