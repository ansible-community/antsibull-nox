# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Git helpers.
"""

from __future__ import annotations

import os
import typing as t

from .command import CommandRunner

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable


class Git(CommandRunner):
    """
    Git command runner.
    """

    def __init__(self, cli: str = "git") -> None:
        super().__init__(prefix=[cli])

    def is_clean(
        self,
        *,
        path: str | os.PathLike[str] | None,
        what: str | os.PathLike[str] | None,
    ) -> bool:
        """
        Determine whether the given path is clean or not.
        """
        args: list[str | os.PathLike[str]] = [
            "status",
            "--porcelain=v1",
            "--untracked=normal",
        ]
        if what is not None:
            args.extend(["--", what])
        result = self.run(args, allow_rc=[0], cwd=path)
        return not result.stdout

    def has_staged_changes(
        self,
        *,
        path: str | os.PathLike[str] | None,
        what: str | os.PathLike[str] | None,
    ) -> bool:
        """
        Determine whether the given path has staged changes (index) or not.
        """
        args: list[str | os.PathLike[str]] = [
            "status",
            "--porcelain=v1",
            "--untracked=no",
        ]
        if what is not None:
            args.extend(["--", what])
        result = self.run(args, allow_rc=[0], cwd=path)
        for line in result.stdout.splitlines():
            if line[0] != " ":
                return True
        return False

    def archive(
        self,
        *,
        commit: str,
        tarball_path: str | os.PathLike[str],
        prefix: str | None = None,
        path: str | os.PathLike[str] | None,
        what: str | os.PathLike[str] | None,
    ) -> None:
        """
        Archive the repository at the given commit.
        """
        args: list[str | os.PathLike[str]] = [
            "archive",
            f"--output={tarball_path}",
        ]
        if prefix is not None:
            args.append(f"--prefix={prefix}")
        args.extend(["--", commit])
        if what is not None:
            args.append(what)
        self.run(args, allow_rc=[0], cwd=path)

    def add(
        self,
        paths: Iterable[str | os.PathLike[str]],
        path: str | os.PathLike[str] | None,
    ) -> None:
        """
        Add given paths to git's stage area (index).
        """
        args: list[str | os.PathLike[str]] = [
            "add",
            "--",
            *paths,
        ]
        self.run(args, allow_rc=[0], cwd=path)

    def commit(
        self,
        *,
        message: str,
        signed: bool = False,
        path: str | os.PathLike[str] | None,
    ) -> None:
        """
        Commit staged changes (index) to git.
        """
        args: list[str | os.PathLike[str]] = [
            "commit",
            "-m",
            message,
        ]
        if signed:
            args.append("--gpg-sign")
        self.run(args, allow_rc=[0], cwd=path)

    def list_tags(
        self, path: str | os.PathLike[str] | None, *, pattern: str | None = None
    ) -> list[str]:
        """
        List all tags.
        """
        args: list[str | os.PathLike[str]] = [
            "tag",
            "--list",
        ]
        if pattern is not None:
            args.extend(["--", pattern])
        result = self.run_text(args, allow_rc=[0], cwd=path)
        return result.stdout.splitlines()

    def tag(
        self,
        *,
        tag: str,
        message: str | None = None,
        signed: bool = False,
        path: str | os.PathLike[str] | None,
    ) -> None:
        """
        Tag the current commit.
        """
        args: list[str | os.PathLike[str]] = [
            "tag",
        ]
        if signed:
            args.append("--sign")
        elif message is not None:
            args.append("--annotate")
        if message is not None:
            args.extend(["-m", message])
        args.extend(["--", tag])
        self.run(args, allow_rc=[0], cwd=path)

    def restore(
        self,
        *,
        path: str | os.PathLike[str] | None,
    ) -> None:
        """
        Remove all staged, unstaged, and untracked changes.
        """
        self.run(["reset", "HEAD", "."], allow_rc=[0], cwd=path)
        self.run(["restore", "."], allow_rc=[0], cwd=path)
        self.run(["clean", "."], allow_rc=[0], cwd=path)

    def remove_last_commit(
        self,
        *,
        hard: bool = False,
        path: str | os.PathLike[str] | None,
    ) -> None:
        """
        Remove the last commit.
        """
        args = ["reset"]
        if hard:
            args.append("--hard")
        args.append("HEAD^")
        self.run(args, allow_rc=[0], cwd=path)

    def remove_tag(
        self,
        tag: str,
        *,
        path: str | os.PathLike[str] | None,
    ) -> None:
        """
        Remove a tag.
        """
        args = ["tag", "--delete", "--", tag]
        self.run(args, allow_rc=[0], cwd=path)


__all__ = ("Git",)
