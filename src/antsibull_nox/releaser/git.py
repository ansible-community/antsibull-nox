# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Git helpers.
"""

from __future__ import annotations

import dataclasses
import os
import subprocess
import typing as t
from pathlib import Path

from semantic_version import Version

from ..collection.data import CollectionData
from ..config import _GitReleaserFragment
from .base import BaseVCSReleaser
from .command import CommandRunner
from .ui import retry

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

    Change = t.Literal["?", "!", "M", "T", "A", "D", "R", "C", "U"]


@dataclasses.dataclass
class GitChange:
    """
    Change in 'git status' output.
    """

    x: Change | None
    y: Change | None
    path: bytes
    renamed_from: bytes | None


class Git(CommandRunner):
    """
    Git command runner.
    """

    def __init__(self, cli: str = "git") -> None:
        super().__init__(prefix=[cli])

    def status(
        self,
        *,
        path: str | os.PathLike[str] | None = None,
        what: str | os.PathLike[str] | None = None,
    ) -> list[GitChange]:
        """
        Determine changes in the given path.
        """
        args: list[str | os.PathLike[str]] = [
            "status",
            "--porcelain=v1",
            "--untracked=normal",
            "-z",
        ]
        if what is not None:
            args.extend(["--", what])
        result = self.run(args, allow_rc=[0], cwd=path)
        lines = result.stdout.split(b"\0")
        res = []
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if len(line) < 3:
                idx += 1
                continue
            x = chr(line[0]) if line[0] != 32 else None
            y = chr(line[1]) if line[1] != 32 else None
            c_path = line[3:]
            c_renamed_from: bytes | None = None
            if x == "R":
                idx += 1
                c_renamed_from = lines[idx]
            res.append(
                GitChange(
                    x=x,  # type: ignore
                    y=y,  # type: ignore
                    path=c_path,
                    renamed_from=c_renamed_from,
                )
            )
            idx += 1
        return res

    def is_clean(
        self,
        *,
        path: str | os.PathLike[str] | None = None,
        what: str | os.PathLike[str] | None = None,
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

    def get_current_commit(
        self,
        *,
        path: str | os.PathLike[str] | None = None,
    ) -> str:
        """
        Get the commit of the current commit.
        """
        result = self.run_text(["rev-parse", "HEAD"], allow_rc=[0], cwd=path)
        return result.stdout.strip()

    def get_current_branch(
        self,
        *,
        path: str | os.PathLike[str] | None = None,
    ) -> str | None:
        """
        Get the current branch.
        """
        result = self.run_text(["branch", "--show-current"], allow_rc=[0], cwd=path)
        return result.stdout.rstrip() or None

    def get_repository_root(
        self,
        *,
        path: str | os.PathLike[str] | None = None,
    ) -> Path:
        """
        Get the repository's root.
        """
        result = self.run_text(["rev-parse", "--show-toplevel"], allow_rc=[0], cwd=path)
        return Path(result.stdout.rstrip("\n"))

    def has_staged_changes(
        self,
        *,
        path: str | os.PathLike[str] | None = None,
        what: str | os.PathLike[str] | None = None,
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
        path: str | os.PathLike[str] | None = None,
        what: str | os.PathLike[str] | None = None,
    ) -> None:
        """
        Archive the repository at the given commit.
        """
        args: list[str | os.PathLike[str]] = [
            "archive",
            "--format=tar",
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
        *,
        path: str | os.PathLike[str] | None = None,
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
        path: str | os.PathLike[str] | None = None,
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
        self, path: str | os.PathLike[str] | None = None, *, pattern: str | None = None
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
        path: str | os.PathLike[str] | None = None,
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

    def restore_to_commit(
        self,
        commit: str = "HEAD",
        *,
        path: str | os.PathLike[str] | None = None,
        clean: bool = True,
    ) -> None:
        """
        Remove all staged, unstaged, and untracked changes.
        If ``commit`` is specified, go back to that commit in the current branch.
        """
        self.run(["reset", "--hard", commit], allow_rc=[0], cwd=path)
        if clean:
            self.run(["clean", "--force", "-d", "."], allow_rc=[0], cwd=path)

    def remove_tag(
        self,
        tag: str,
        *,
        path: str | os.PathLike[str] | None = None,
    ) -> None:
        """
        Remove a tag.
        """
        args = ["tag", "--delete", "--", tag]
        self.run(args, allow_rc=[0], cwd=path)


class GitReleaser(BaseVCSReleaser):
    """
    Git VCS releaser.
    """

    def __init__(self, config: _GitReleaserFragment) -> None:
        self.__config = config
        self.__git = Git()

    def __check(self) -> tuple[Path, Path]:
        cwd = Path.cwd()

        root = self.__git.get_repository_root()
        branch = self.__git.get_current_branch()
        if branch != self.__config.release_branch:
            raise ValueError(
                f"Expected to be in branch {self.__config.release_branch}"
                f" for releasing, but are in branch {branch}!"
            )
        status = self.__git.status(path=root)
        danger_paths = [
            (str(p) + (os.sep if is_dir else "")).encode("utf-8")
            for p, is_dir in [
                (self.__config.collection_root / "changelogs" / "fragments", True),
                (self.__config.collection_root / "galaxy.yml", False),
            ]
        ]
        for s in status:
            if s.x != "?":
                raise ValueError("Git repository is not clean.")
            if any(s.path.startswith(p) for p in danger_paths):
                raise ValueError(
                    f"Git repository has dangerous untracked path {s.path.decode('utf-8')}"
                )
        coll = root / self.__config.collection_root

        act_cwd = cwd.resolve()
        act_coll = coll.resolve()
        if act_cwd != act_coll:
            raise ValueError(
                f"Git repository root is {root.resolve()}, therefore the collection root"
                f" should be {act_coll}, but we are in {act_cwd}!"
            )

        return root, coll

    def create_vcs_release(
        self, *, collection: CollectionData, version: Version
    ) -> None:
        """
        Create release in VCS.

        Ensure we're in the right branch, create release commit(s) and tag(s).
        """
        root, coll = self.__check()
        if collection.version != str(version):
            raise ValueError(
                f"galaxy.yml's version is {collection.version}, expected {version}!"
            )

        commit = self.__git.get_current_commit(path=root)
        try:
            # Update changelog
            args = ["antsibull-changelog", "release", "--reload-plugins"]
            if version.minor == 0 and version.bugfix == 0:
                args.append("--cummulative-release")
            subprocess.run(args, cwd=coll, check=True)

            # Stage changes
            status = self.__git.status(path=root, what=self.__config.collection_root)
            changed_paths = []
            for s in status:
                if s.x in ("?", "!"):
                    continue
                changed_paths.append(s.path.decode("utf-8"))
                if s.renamed_from is not None:
                    changed_paths.append(s.renamed_from.decode("utf-8"))
            if not changed_paths:
                raise ValueError(
                    "Found no changes for release commit. Has the release already been done?"
                )
            self.__git.add(changed_paths, path=root)

            # Create release commit
            release_commit_message = self.__config.release_commit_message.replace(
                "{version}", str(version)
            )
            retry(
                lambda: self.__git.commit(
                    message=release_commit_message,
                    signed=self.__config.sign_commits,
                    path=root,
                ),
                what="Create release commit",
            )

            # Create release tag
            release_tag_message = self.__config.release_tag_message.replace(
                "{version}", str(version)
            )
            tag = self.__config.tag_format.replace("{version}", str(version))
            retry(
                lambda: self.__git.tag(
                    tag=tag,
                    message=release_tag_message,
                    signed=self.__config.sign_tags,
                    path=root,
                ),
                what="Create release tag",
            )
        except BaseException:
            self.__git.restore_to_commit(commit, path=root, clean=False)
            raise


__all__ = ("Git", "GitReleaser")
