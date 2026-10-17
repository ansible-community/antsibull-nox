# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Galaxy helpers.
"""

from __future__ import annotations

import datetime
import hashlib
import typing as t
from pathlib import Path
from urllib.parse import quote_plus

import pydantic as p
from semantic_version import Version

from ._http import RequestsSession


def _validate(
    filename: str, calc_digest: str, orig_digest: str, hash_name: str
) -> None:
    if calc_digest.lower() != orig_digest.lower():
        raise ValueError(
            f"Failed to check {hash_name} for {filename}: expected {orig_digest}, got {calc_digest}"
        )


def _validate_file(
    filename: str,
    digest: tuple[str, hashlib._Hash, str] | None,
    file: t.IO[bytes],
    *,
    size: int | None = None,
) -> None:
    if digest is None:
        return
    orig_digest, h, hash_name = digest
    actual_size = 0
    try:
        while True:
            data = file.read(65536)
            if not data:
                break
            actual_size += len(data)
            h.update(data)
    except IOError as exc:
        raise ValueError(f"I/O error while validating {filename}: {exc}") from exc
    if size is not None and size != actual_size:
        raise ValueError(
            f"Expected {filename} to have {size} bytes, but it has {actual_size} bytes"
        )
    _validate(filename, h.hexdigest(), orig_digest, hash_name)


def _validate_content(
    filename: str,
    digest: tuple[str, hashlib._Hash, str] | None,
    data: bytes,
    *,
    size: int | None = None,
) -> None:
    if size is not None and size != len(data):
        raise ValueError(
            f"Expected {filename} to have {size} bytes, but it has {len(data)} bytes"
        )
    if digest is None:
        return
    orig_digest, h, hash_name = digest
    h.update(data)
    _validate(filename, h.hexdigest(), orig_digest, hash_name)


def _validate_path(
    filename: str,
    digest: tuple[str, hashlib._Hash, str] | None,
    path: Path,
    *,
    size: int | None = None,
) -> None:
    if digest is None:
        return
    try:
        with path.open("rb") as f:
            _validate_file(filename, digest, f, size=size)
    except IOError as exc:
        raise ValueError(f"I/O error while validating {filename}: {exc}") from exc


class Artifact(p.BaseModel):
    """
    Artifact information of a Galaxy release.
    """

    filename: str
    sha256: t.Optional[str] = None
    size: t.Optional[int] = None

    def _get_digest(self) -> tuple[str, hashlib._Hash, str] | None:
        if self.sha256 is None:
            return None
        return (self.sha256, hashlib.sha256(), "SHA-256")

    def validate_file(self, file: t.IO[bytes]) -> None:
        """
        Validate file contents against stored digest.
        """
        _validate_file(self.filename, self._get_digest(), file, size=self.size)

    def validate_content(self, data: bytes) -> None:
        """
        Validate file contents against stored digest.
        """
        _validate_content(self.filename, self._get_digest(), data, size=self.size)

    def validate_path(self, path: Path) -> None:
        """
        Validate file contents against stored digest.
        """
        _validate_path(self.filename, self._get_digest(), path, size=self.size)


class Namespace(p.BaseModel):
    """
    Namespace information.
    """

    name: str


class ContentEntry(p.BaseModel):
    """
    Content information entry.
    """

    name: str
    description: t.Optional[str] = None
    content_type: str


class Metadata(p.BaseModel):
    """
    Collection metadata.
    """

    authors: list[str] = []
    contents: list[ContentEntry] = []
    dependencies: dict[str, str] = {}
    description: t.Optional[str] = None
    documentation: t.Optional[str] = None
    homepage: t.Optional[str] = None
    issues: t.Optional[str] = None
    license: list[str] = []
    repository: t.Optional[str] = None
    tags: list[str] = []


class CollectionInfo(p.BaseModel):
    """
    Collection information.
    """

    name: str
    namespace: str
    version: str
    dependencies: dict[str, str] = {}
    tags: list[str] = []
    issues: t.Optional[str] = None
    readme: t.Optional[str] = None
    authors: list[str] = []
    license: list[str] = []
    homepage: t.Optional[str] = None
    repository: t.Optional[str] = None
    description: t.Optional[str] = None
    license_file: t.Optional[str] = None
    documentation: t.Optional[str] = None


class ManifestEntry(p.BaseModel):
    """
    Manifest entry.
    """

    name: str
    ftype: t.Literal["file", "dir"]
    format: t.Literal[1]
    chksum_type: t.Optional[str] = None
    chksum_sha256: t.Optional[str] = None

    def _get_digest(self) -> tuple[str, hashlib._Hash, str] | None:
        if self.chksum_sha256 is None:
            return None
        return (self.chksum_sha256, hashlib.sha256(), "SHA-256")

    def validate_file(self, file: t.IO[bytes]) -> None:
        """
        Validate file contents against stored digest.
        """
        _validate_file(self.name, self._get_digest(), file)

    def validate_content(self, data: bytes) -> None:
        """
        Validate file contents against stored digest.
        """
        _validate_content(self.name, self._get_digest(), data)

    def validate_path(self, path: Path) -> None:
        """
        Validate file contents against stored digest.
        """
        _validate_path(self.name, self._get_digest(), path)


class Manifest(p.BaseModel):
    """
    Manifest content.
    """

    format: int
    collection_info: CollectionInfo
    file_manifest_file: ManifestEntry


class Files(p.BaseModel):
    """
    Files information.
    """

    format: t.Literal[1]
    files: list[ManifestEntry] = []


class ReleaseInfo(p.BaseModel):
    """
    Information on a collection release.
    """

    version: str
    created_at: t.Optional[datetime.datetime] = None
    updated_at: t.Optional[datetime.datetime] = None
    requires_ansible: t.Optional[str] = None
    artifact: Artifact
    download_url: str
    name: t.Optional[str] = None
    namespace: Namespace
    signatures: list[t.Any] = []
    metadata: Metadata
    manifest: t.Optional[Manifest] = None
    files: t.Optional[Files] = None


def q(value: str) -> str:
    """
    Quote value for URLs.
    """
    return quote_plus(value, encoding="utf-8")


class GalaxyClient(RequestsSession):
    """
    Basic Galaxy client.
    """

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self._base_url = base_url.rstrip("/")

    def get_specific_release(
        self, namespace: str, name: str, version: Version
    ) -> ReleaseInfo | None:
        """
        Get release information for a specific release.
        """
        url = (
            f"{self._base_url}/v3/collections/{q(namespace)}/{q(name)}/"
            f"versions/{q(str(version))}/"
        )
        r = self._get(url, expected=[200, 404], timeout=10)
        if r.status_code == 404:
            return None
        try:
            data = r.json()
            return ReleaseInfo.model_validate(data)
        except Exception as exc:
            raise ValueError(f"Error while parsing GET {url} response: {exc}") from exc

    def download_release(self, release: ReleaseInfo, path: Path) -> None:
        """
        Download a release's tarball.
        """
        self._download_file(release.download_url, path)


__all__ = (
    "Artifact",
    "ContentEntry",
    "Metadata",
    "CollectionInfo",
    "ManifestEntry",
    "Manifest",
    "Files",
    "ReleaseInfo",
    "Namespace",
    "GalaxyClient",
)
