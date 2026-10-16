# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Command runner helpers.
"""

from __future__ import annotations

import abc
import contextlib
import os
import shlex
import subprocess
import sys
import typing as t
from pathlib import Path

from .ui import prompt_user

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Iterable, Mapping

    _T = t.TypeVar("_T")

    class RunKwargs(t.TypedDict):
        """
        Keyword arguments for generic run functions.
        """

        input: t.NotRequired[bytes | None]
        cwd: t.NotRequired[str | os.PathLike | None]
        timeout: t.NotRequired[float | None]
        env: t.NotRequired[Mapping[str, str] | None]


def _lossy_decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _opt_lossy_decode(value: str | bytes) -> str:
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


class CommandRunner(metaclass=abc.ABCMeta):
    """
    Command runner.
    """

    def __init__(self, *, prefix: list[str]) -> None:
        self.prefix = prefix

    def check_rc(
        self,
        *,
        args: list[str],
        returncode: int,
        stdout: str | bytes,
        stderr: str | bytes,
        allow_rc: int | Iterable[int],
    ) -> None:
        """
        Check whether the command passed.

        Raise ``ValueError`` if not.
        """
        if isinstance(allow_rc, int):
            allow_rc = [allow_rc]
        if returncode not in allow_rc:
            messages = [
                f"Running {shlex.join(args)} resulted in unexpected exit code {returncode}."
            ]
            if stdout:
                messages.append(f"stdout:\n{_opt_lossy_decode(stdout)}")
            if stderr:
                messages.append(f"stderr:\n{_opt_lossy_decode(stderr)}")
            raise ValueError("\n\n".join(messages))

    def _check_rc(
        self, p: subprocess.CompletedProcess, *, allow_rc: int | Iterable[int]
    ) -> None:
        self.check_rc(
            args=p.args,
            returncode=p.returncode,
            stdout=p.stdout,
            stderr=p.stderr,
            allow_rc=allow_rc,
        )

    def run(
        self,
        args: Iterable[str | os.PathLike[str] | None],
        *,
        allow_rc: int | Iterable[int] | None = None,
        **kwargs: t.Unpack[RunKwargs],
    ) -> subprocess.CompletedProcess[bytes]:
        """
        Run command and capture output as bytes.
        """

        p = subprocess.run(
            self.prefix + [str(arg) for arg in args if arg is not None],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            **kwargs,
        )
        if allow_rc is not None:
            self._check_rc(p, allow_rc=allow_rc)
        return p

    def run_text(
        self,
        args: Iterable[str | os.PathLike[str]],
        *,
        allow_rc: int | Iterable[int] | None = None,
        **kwargs: t.Unpack[RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        """
        Run command and capture output as Unicode strings.
        """

        p = subprocess.run(
            self.prefix + [str(arg) for arg in args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            check=False,
            **kwargs,
        )
        if allow_rc is not None:
            self._check_rc(p, allow_rc=allow_rc)
        return p


def repeat_if_failed(
    command: Callable[[], _T], *, postprocess: Callable[[_T], _T] | None = None
) -> _T:
    """
    Run command. In case of failure (ValueError), ask user whether to repeat it or not.
    """
    while True:
        try:
            result = command()
            if postprocess is not None:
                result = postprocess(result)
            return result
        except ValueError as exc:
            retry = True
            if sys.stdout.isatty():
                print(str(exc), file=sys.stderr)
                retry = (
                    prompt_user(
                        "Do you want to retry?",
                        accept=["y", "n"],
                        default="y",
                        abort="n",
                    )
                    == "y"
                )
            else:
                print("No TTY found, do not ask user to try again.", file=sys.stderr)
            if not retry:
                raise


@contextlib.contextmanager
def chdir(path: Path) -> t.Generator[None]:
    """
    Context manager for temporarily changing the current directory.
    """
    cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


__all__ = ("CommandRunner", "chdir", "repeat_if_failed")
