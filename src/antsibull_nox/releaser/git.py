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
import typing as t
from collections import defaultdict
from pathlib import Path

from antsibull_changelog.changes import ChangesData
from antsibull_changelog.config import ChangelogConfig, TextFormat
from antsibull_fileutils.yaml import store_yaml_file
from semantic_version import Version

from ..collection.data import CollectionData
from ..collection.search import GALAXY_YML
from ..config import CONFIG_FILENAME
from ..config import Releaser as ReleaserConfig
from ..config import VersionBump, _GitReleaserFragment
from ._template import template_string
from ._version import get_next_version
from ._yaml import YAMLEditor
from .base import BaseVCSReleaser, ReleasePreview
from .changelog import (
    check_for_release_summary,
    get_changelog_config_and_files,
    lint_fragment_content,
    load_changelog,
    make_release,
    render_changelog_extract,
)
from .command import CommandRunner, repeat_if_failed

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

    def push_remote_tag(
        self,
        *,
        tag: str,
        remote: str,
        path: str | os.PathLike[str] | None = None,
    ) -> None:
        """
        Push the tag to the remote.
        """
        args: list[str | os.PathLike[str]] = [
            "push",
            "--",
            remote,
            tag,
        ]
        self.run(args, allow_rc=[0], cwd=path)

    def remove_remote_tag(
        self,
        *,
        tag: str,
        remote: str,
        path: str | os.PathLike[str] | None = None,
    ) -> None:
        """
        Remove the tag from the remote.
        """
        args: list[str | os.PathLike[str]] = [
            "push",
            "--",
            remote,
            f":{tag}",
        ]
        self.run(args, allow_rc=[0], cwd=path)

    def get_object_type(
        self,
        *,
        ref: str,
        path: str | os.PathLike[str] | None = None,
    ) -> str | None:
        """
        Return type of object ``ref`` (basically what 'git cat-file -t <ref>' returns).
        Return ``None`` in case the object does not exist.
        """
        args: list[str | os.PathLike[str]] = [
            "cat-file",
            "-t",
            "--",
            ref,
        ]
        result = self.run_text(args, allow_rc=[0, 128], cwd=path)
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def show(
        self,
        *,
        file: str | os.PathLike[str],
        ref: str,
        path: str | os.PathLike[str] | None = None,
    ) -> bytes | None:
        """
        Given a file and a reference, obtain the file's contents in that version of the tree.
        Returns ``None`` if the file or tree does not exist.
        """
        # Does not work with '--', so we do some manual checking that ref isn't wrongly interpreted:
        if ref.startswith("-"):
            raise ValueError(f"Invalid Git object reference: {ref!r}")
        args: list[str | os.PathLike[str]] = [
            "show",
            f"{ref}:{file}",
        ]
        result = self.run(args, allow_rc=[0, 128], cwd=path)
        if result.returncode != 0:
            return None
        return result.stdout


class GitReleaser(BaseVCSReleaser):
    """
    Git VCS releaser.
    """

    def __init__(self, config: _GitReleaserFragment) -> None:
        self.__config = config
        self.__git = Git()

    def is_vcs_config_close_enough(self, *, other_config: ReleaserConfig) -> bool:
        """
        Check whether the provided VCS releaser config is "close enough" to the current config.
        """
        if not isinstance(other_config, _GitReleaserFragment):
            return False
        return other_config.git_tag_format == self.__config.git_tag_format

    def __check(
        self,
        version: Version,
        *,
        clean_changelog_data: bool = True,
        clean_changelogs: bool = False,
    ) -> tuple[Path, Path, ChangelogConfig, list[Path]]:
        cwd = Path.cwd()

        _, config, changelogs = get_changelog_config_and_files(version=version)

        danger_paths_raw: list[tuple[Path, bool]] = [
            (self.__config.git_collection_root / GALAXY_YML, False),
        ]
        if clean_changelog_data:
            danger_paths_raw.extend(
                [
                    (
                        self.__config.git_collection_root
                        / "changelogs"
                        / config.notes_dir,
                        True,
                    ),
                    (
                        self.__config.git_collection_root
                        / "changelogs"
                        / config.changes_file,
                        False,
                    ),
                ]
            )
        if clean_changelogs:
            danger_paths_raw.extend(
                (
                    (self.__config.git_collection_root / changelog, False)
                    for changelog in changelogs
                )
            )

        root = self.__git.get_repository_root()
        branch = self.__git.get_current_branch()
        if branch != self.__config.git_release_branch:
            raise ValueError(
                f"Expected to be in branch {self.__config.git_release_branch}"
                f" for releasing, but are in branch {branch}!"
            )
        status = self.__git.status(path=root)
        danger_paths = [
            (str(p) + (os.sep if is_dir else "")).encode("utf-8")
            for p, is_dir in danger_paths_raw
        ]
        for s in status:
            if s.x != "?":
                raise ValueError("Git repository is not clean.")
            if any(s.path.startswith(p) for p in danger_paths):
                raise ValueError(
                    f"Git repository has dangerous untracked path {s.path.decode('utf-8')}"
                )
        coll = root / self.__config.git_collection_root

        act_cwd = cwd.resolve()
        act_coll = coll.resolve()
        if act_cwd != act_coll:
            raise ValueError(
                f"Git repository root is {root.resolve()}, therefore the collection root"
                f" should be {act_coll}, but we are in {act_cwd}!"
            )

        return root, coll, config, changelogs

    def prepare_vcs_release(
        self, *, collection: CollectionData, version: Version, release_summary: str
    ) -> None:
        """
        Prepare a release in VCS.

        Ensure we're in the right branch, update version and create release summary,
        and then create preparation commit(s).
        """
        root, _, changelog_config, _ = self.__check(version)

        galaxy_yml = root / self.__config.git_collection_root / GALAXY_YML
        changelog_fragment = (
            root
            / self.__config.git_collection_root
            / "changelogs"
            / "fragments"
            / f"{version}.yml"
        )

        if changelog_fragment.exists():
            raise ValueError(
                f"The release summary changelog fragment {changelog_fragment}"
                f" for {version} already exists!"
            )
        existing_summary = check_for_release_summary()
        if existing_summary is not None:
            raise ValueError(
                "There already exists a release summary changelog fragment:"
                f" {existing_summary[0].path}"
            )

        sign_commit = self.__config.git_sign_other_commits
        if sign_commit is None:
            sign_commit = self.__config.git_sign_commits
        commit_message = template_string(
            self.__config.git_prepare_commit_message,
            variables={"version": str(version)},
        )

        fragment = {
            changelog_config.prelude_name: release_summary,
        }
        fragment_errors = lint_fragment_content(
            config=changelog_config, fragment_content=fragment
        )
        if fragment_errors:
            errors = "\n".join(
                (f"{line}:{col}:{message}" for line, col, message in fragment_errors)
            )
            raise ValueError(f"Error while linting the changelog fragment:\n{errors}")

        commit = self.__git.get_current_commit(path=root)
        try:
            # Update version in galaxy.yml
            galaxy = YAMLEditor(path=galaxy_yml)
            field = galaxy.find(key="version")
            if field is None:
                field = galaxy.create(key="version", value="")
            version_str = str(version)
            if field.value != version_str:
                field.set(version_str)
                galaxy.write()

            # Write changelog fragment
            store_yaml_file(changelog_fragment, fragment, nice=True)

            # Stage changes
            self.__git.add([galaxy_yml, changelog_fragment], path=root)

            # Create release commit
            repeat_if_failed(
                lambda: self.__git.commit(
                    message=commit_message,
                    signed=sign_commit,
                    path=root,
                ),
            )
        except BaseException:
            self.__git.restore_to_commit(commit, path=root, clean=False)
            raise

    def _get_changed_paths(self, root: Path) -> list[str]:
        status = self.__git.status(path=root, what=self.__config.git_collection_root)
        changed_paths = []
        for s in status:
            if s.x in ("?", "!"):
                continue
            changed_paths.append(s.path.decode("utf-8"))
            if s.renamed_from is not None:
                changed_paths.append(s.renamed_from.decode("utf-8"))
        return changed_paths

    def has_vcs_release(self, *, version: Version) -> bool:
        """
        Check whether a release already exists in VCS.
        """
        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )
        root = self.__git.get_repository_root()
        tags = self.__git.list_tags(path=root, pattern=tag)
        return tag in tags

    def get_config_file_from_release(
        self, *, version: Version
    ) -> tuple[bool, bytes | None]:
        """
        Check whether a release already exists in VCS, and returns its antsibull-nox configuration.

        The return value ``(exists, contents)`` consists out of a boolean
        ``exists`` whether the release exists, and a bytes string ``contents``
        that contains the contents of antsibull-nox.toml if it exists for that release.
        """
        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )
        ref = f"refs/tags/{tag}"
        root = self.__git.get_repository_root()
        objtype = self.__git.get_object_type(ref=ref, path=root)
        if objtype not in ("commit", "tag"):
            return False, None
        result = self.__git.show(
            file=self.__config.git_collection_root / CONFIG_FILENAME,
            ref=ref,
            path=root,
        )
        return True, result

    def create_vcs_release(
        self, *, collection: CollectionData, version: Version
    ) -> None:
        """
        Create release in VCS.

        Ensure we're in the right branch, create release commit(s) and tag(s).
        """
        root, _, changelog_config, changelogs = self.__check(
            version, clean_changelogs=True
        )
        if collection.version != str(version):
            raise ValueError(
                f"galaxy.yml's version is {collection.version}, expected {version}!"
            )

        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )
        release_commit_message = template_string(
            self.__config.git_release_commit_message,
            variables={"version": str(version)},
        )
        release_tag_message = template_string(
            self.__config.git_release_tag_message, variables={"version": str(version)}
        )

        commit = self.__git.get_current_commit(path=root)
        try:
            # Update changelog
            make_release(version, cummulative_release=True)

            # Stage changes
            changed_paths = [
                self.__config.git_collection_root
                / "changelogs"
                / changelog_config.notes_dir,
                self.__config.git_collection_root
                / "changelogs"
                / changelog_config.changes_file,
                *(
                    self.__config.git_collection_root / changelog
                    for changelog in changelogs
                ),
            ]
            self.__git.add(changed_paths, path=root)

            # Create release commit
            repeat_if_failed(
                lambda: self.__git.commit(
                    message=release_commit_message,
                    signed=self.__config.git_sign_commits,
                    path=root,
                ),
            )

            # Create release tag
            repeat_if_failed(
                lambda: self.__git.tag(
                    tag=tag,
                    message=release_tag_message,
                    signed=self.__config.git_sign_tags,
                    path=root,
                ),
            )
        except BaseException:
            self.__git.restore_to_commit(commit, path=root, clean=False)
            raise

    def create_release_source_tarball(
        self, *, tarball_path: Path, version: Version
    ) -> str | None:
        """
        Create tarball (.tar) of a tagged release. Return prefix that all entries have.
        """
        tag = template_string(
            self.__config.git_tag_format, variables={"version": str(version)}
        )
        prefix_str: str | None = str(self.__config.git_collection_root)
        prefix: str | None
        if prefix_str == ".":
            prefix, prefix_str = None, None
        else:
            prefix, prefix_str = prefix_str, f"{prefix_str}/"
        root = self.__git.get_repository_root()
        self.__git.archive(
            commit=tag,
            tarball_path=tarball_path,
            prefix=prefix_str,
            path=root,
            what=prefix,
        )
        return prefix

    def bump_version(
        self,
        *,
        collection: CollectionData,
        new_version: Version | None = None,
        bump: VersionBump | None = None,
        commit_message: str | None = None,
    ) -> Version | None:
        """
        Bump the version after a release.

        One of ``bump`` and ``new_version`` must be provided.
        If none is provided, a fallback value is taken from the config.
        If that is not available, the call will fail.

        Similarly for the commit message.

        Returns the new version if it was set.
        """
        if new_version is not None and bump is not None:
            raise ValueError("Cannot specify both new_version and bump!")
        if new_version is None:
            if not collection.version:
                raise ValueError(
                    "The collection has no current version, so we cannot determine the next one."
                )
            try:
                current_version = Version(collection.version)
            except Exception as exc:
                raise ValueError(
                    f"Cannot parse collection version {collection.version!r}: {exc}"
                ) from exc
            if bump is not None:
                new_version = get_next_version(current_version, bump)
            elif self.__config.git_post_release_bump is not None:
                new_version = get_next_version(
                    current_version, self.__config.git_post_release_bump
                )
            else:
                raise ValueError(
                    "You need to specify a new version, or how to bump the current version."
                )

        root, _, _, _ = self.__check(version=None, clean_changelog_data=False)
        galaxy_yml = root / self.__config.git_collection_root / GALAXY_YML

        sign_commit = self.__config.git_sign_other_commits
        if sign_commit is None:
            sign_commit = self.__config.git_sign_commits

        if commit_message is None:
            if self.__config.git_post_release_commit_message is None:
                raise ValueError("You need to specify a commit message.")
            commit_message = template_string(
                self.__config.git_post_release_commit_message,
                variables={
                    "new-version": str(new_version),
                    "old-version": collection.version or "",
                },
            )

        commit = self.__git.get_current_commit(path=root)
        try:
            # Update version in galaxy.yml
            galaxy = YAMLEditor(path=galaxy_yml)
            field = galaxy.find(key="version")
            if field is None:
                field = galaxy.create(key="version", value="")
            version_str = str(new_version)
            if field.value == version_str:
                # Version already set - return.
                return None
            field.set(version_str)
            galaxy.write()

            # Stage changes
            self.__git.add([galaxy_yml], path=root)

            # Create release commit
            repeat_if_failed(
                lambda: self.__git.commit(
                    message=commit_message,
                    signed=sign_commit,
                    path=root,
                ),
            )
            return new_version
        except BaseException:
            self.__git.restore_to_commit(commit, path=root, clean=False)
            raise

    def _get_previous_release(
        self,
        *,
        collection_version: Version | None,
        changes_data: ChangesData,
    ) -> Version | None:
        if collection_version and self.has_vcs_release(version=collection_version):
            if str(collection_version) not in changes_data.releases:
                raise ValueError(
                    f"Current version {collection_version} has a VCS release,"
                    " but does not appear in changelog!"
                )
            if changes_data.latest_version != str(collection_version):
                raise ValueError(
                    f"Current version {collection_version} is before the latest release"
                    f" in the changelog ({changes_data.latest_version})!"
                )
            return collection_version
        if changes_data.has_release:
            try:
                return Version(changes_data.latest_version)
            except Exception as exc:
                raise ValueError(
                    "Error while parsing the latest"
                    f" changelog version {changes_data.latest_version!r}: {exc}"
                ) from exc
        return None

    def vcs_preview(
        self,
        *,
        collection: CollectionData,
        allow_plugin_cache: bool = False,
    ) -> ReleasePreview:
        """
        Collect a release preview.
        """
        collection_version: Version | None = None
        if collection.version:
            try:
                collection_version = Version(collection.version)
            except Exception as exc:
                raise ValueError(
                    f"Error while parsing the collection version {collection.version!r}: {exc}"
                ) from exc

        commit = self.__git.get_current_commit()
        if collection_version:
            cache_version = Version(
                major=collection_version.major,
                minor=collection_version.minor,
                patch=collection_version.patch,
                prerelease=collection_version.prerelease + (commit,),
            )
        else:
            cache_version = Version(major=0, minor=0, patch=0, prerelease=(commit,))

        _, collection_details, config, changes_data, fragments, plugins = (
            load_changelog(
                cache_version=cache_version,
                allow_plugin_cache=allow_plugin_cache,
            )
        )
        previous_release = self._get_previous_release(
            collection_version=collection_version,
            changes_data=changes_data,
        )

        # Determine changes
        change_count: dict[str, int] = defaultdict(int)
        for fragment in fragments:
            for section, values in fragment.content.items():
                change_count[section] += 1 if isinstance(values, str) else len(values)
        section_names: dict[str, str] = {}
        section_names[config.prelude_name] = config.prelude_title
        section_names.update(config.sections)

        # Determine new plugins
        new_plugins = []
        for plugin in plugins:
            if not plugin.version_added:
                continue
            try:
                v = Version(plugin.version_added)
            except Exception as exc:
                raise ValueError(
                    f"Error while parsing version_added for plugin {plugin}: {exc}!"
                ) from exc
            if previous_release is None or previous_release < v:
                new_plugins.append(plugin)

        changelog = render_changelog_extract(
            fragments=fragments,
            plugins=new_plugins,
            collection_details=collection_details,
            config=config,
            text_format=TextFormat.RESTRUCTURED_TEXT,
            renderer_kwargs={},
        )

        return ReleasePreview(
            previous_release=previous_release,
            current_version=collection_version,
            changelog_section_count=change_count,
            changelog_section_names=section_names,
            changelog_new_plugins=len(new_plugins),
            changelog_txt=changelog,
            has_features=change_count["minor_changes"] > 0,
            has_new_plugins=len(new_plugins) > 0,
            has_deprecations=change_count["deprecated_features"] > 0,
            has_bugfixes=any(
                change_count[s] > 0 for s in ("bugfixes", "security_fixes")
            ),
            has_major_changes=change_count["major_changes"] > 0,
            has_breaking_changes=any(
                change_count[s] > 0 for s in ("breaking_changes", "removed_features")
            ),
        )


__all__ = ("Git", "GitReleaser")
