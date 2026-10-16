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
import time
import typing as t

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    _T = t.TypeVar("_T")

    LogFunction = Callable[[str], None]


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

    def log(msg: str) -> None:
        print(msg)

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
    accept: list[str],
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
        print(f"Value {value!r} is not acceptable. Try again.")


def retry(action: Callable[[], _T], *, what: str, num_retries: int = 3) -> _T:
    """
    Retry an action at most ``num_retries`` times in case of ``ValueError``s.
    """
    for index in range(num_retries):
        try:
            return action()
        except ValueError as exc:
            print(f"{what} failed with {exc}, retrying... ({index + 1}/{num_retries})")
    return action()


__all__ = ("Retry", "prompt_user", "wait_for")
