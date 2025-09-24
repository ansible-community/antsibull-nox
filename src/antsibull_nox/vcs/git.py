# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Git specific code.
"""

from __future__ import annotations

import subprocess
import typing as t
from pathlib import Path

from . import VcsProvider


class GitProvider(VcsProvider):
    """
    Provides an interface to Git.
    """

    def __init__(self, git_executable: Path) -> None:
        """
        Create a GitProvider instance.
        """
        self.git_executable = git_executable

    @t.overload
    def run(
        self,
        *args: str | Path,
        check_rc: bool = False,
        decode: t.Literal[False] = False,
    ) -> tuple[int, bytes, str]: ...

    @t.overload
    def run(
        self, *args: str | Path, check_rc: bool = False, decode: t.Literal[True]
    ) -> tuple[int, str, str]: ...

    def run(
        self, *args: str | Path, check_rc: bool = False, decode: bool = False
    ) -> tuple[int, str | bytes, str]:
        """
        Run a git command.
        """
        command = [self.git_executable] + [str(arg) for arg in args]
        p = subprocess.run(command, capture_output=True, check=check_rc)
        return (
            p.returncode,
            p.stdout.decode("utf-8") if decode else p.stdout,
            p.stderr.decode("utf-8"),
        )

    def get_all_local_branches(self, *, repo: Path) -> list[str]:
        """
        Get a list of all local branches of the repo.
        """
        _, stdout, __ = self.run(
            "-C",
            repo,
            "for-each-ref",
            "--format",
            "%(refname:strip=2)",
            "--",
            "refs/heads/",
            check_rc=True,
            decode=True,
        )
        return [entry for entry in stdout.splitlines() if entry]

    def get_all_matching_local_branches(
        self, *, repo: Path, branch_patterns: list[str]
    ) -> list[str]:
        """
        Get a list of all local branches of the repo that match one of the given patterns.
        """
        if not branch_patterns:
            return []
        _, stdout, __ = self.run(
            "-C",
            repo,
            "for-each-ref",
            "--format",
            "%(refname:strip=2)",
            "--",
            *(f"refs/heads/{pattern}" for pattern in branch_patterns),
            check_rc=True,
            decode=True,
        )
        return [entry for entry in stdout.splitlines() if entry]

    def get_list(
        self,
        *args: str | Path,
        repo: Path,
        separator: str,
    ) -> list[str]:
        """
        Execute a command that returns a list of strings separated by ``separator``.
        """
        _, stdout, __ = self.run(
            "-C",
            repo,
            *args,
            check_rc=True,
            decode=True,
        )
        to_split = stdout.removesuffix(separator)
        if not to_split:
            return []
        return list(to_split.split(separator))

    def get_branch_fork_point(self, *, repo: Path, branch: str) -> str | None:
        """
        Return a reference to the point at which the given branch was forked.
        """
        # See https://github.com/ansible/ansible/pull/79734 for details.
        rc, stdout, _ = self.run(
            "-C", repo, "merge-base", "--", branch, "HEAD", decode=True
        )
        out = stdout.strip()
        if rc != 0 or not out:
            return None
        return out

    def find_repo_path(self, *, path: Path) -> Path | None:
        """
        Given a path, finds the associated repository path for this VCS,
        if there is one.
        """
        rc, stdout, _ = self.run(
            "-C",
            path,
            "rev-parse",
            "--path-format=absolute",
            "--show-toplevel",
            decode=True,
        )
        out = stdout.strip()
        if rc != 0 or not out:
            return None
        return Path(out)

    def get_current_branch(self, *, repo: Path) -> str | None:
        """
        Retrieve the current branch of the repository.

        If there is no current branch for some reason (detached HEAD state),
        ``None`` is returned.
        """
        rc, stdout, _ = self.run(
            "-C",
            repo,
            "symbolic-ref",
            "--short",
            "--",
            "HEAD",
            check_rc=False,
            decode=True,
        )
        out = stdout.strip()
        if rc != 0 or not out:
            return None
        return out

    def get_changes_compared_to(self, *, repo: Path, branch: str) -> list[Path]:
        """
        Retrieve a list of files and directories that have been added, changed, or removed.

        The returned paths are relative to ``repo``!
        """
        fork_point = self.get_branch_fork_point(repo=repo, branch=branch)
        if fork_point is None:
            raise ValueError(
                f"Cannot determine fork point from current branch/HEAD to {branch}!"
            )

        untracked = self.get_list(
            "ls-files",
            "-z",
            "--others",
            "--exclude-standard",
            repo=repo,
            separator="\0",
        )
        committed = self.get_list(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            fork_point,
            "HEAD",
            repo=repo,
            separator="\0",
        )
        staged = self.get_list(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            "--cached",
            repo=repo,
            separator="\0",
        )
        unstaged = self.get_list(
            "diff", "--name-only", "--no-renames", "-z", repo=repo, separator="\0"
        )

        all_files = untracked + committed + staged + unstaged
        return [Path(file) for file in sorted(set(all_files))]


__all__ = ("GitProvider",)
