# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

"""
Tests for the collection.install module
"""

from __future__ import annotations

from pathlib import Path

import pytest

from antsibull_nox.collection.data import (
    CollectionData,
)
from antsibull_nox.collection.install import (
    _add_all_dependencies,
    _extract_collections_from_extra_deps_file,
    _MissingDependencies,
)
from antsibull_nox.collection.search import (
    CollectionList,
)


def test__add_all_dependencies() -> None:
    path = Path.cwd()
    all_collections = CollectionList.create(
        {
            c.full_name: c
            for c in [
                CollectionData.create(path=path, full_name="foo.bar", current=True),
                CollectionData.create(
                    path=path, full_name="foo.bam", dependencies={"foo.bar": "*"}
                ),
                CollectionData.create(
                    path=path,
                    full_name="foo.baz",
                    dependencies={"foo.bar": "*", "foo.bam": ">= 1.0.0"},
                ),
                CollectionData.create(
                    path=path, full_name="foo.foo", dependencies={"foo.bam": "*"}
                ),
                CollectionData.create(
                    path=path,
                    full_name="foo.error",
                    dependencies={"foo.does_not_exist": "*"},
                ),
            ]
        }
    )

    # No deps
    deps: dict[str, CollectionData] = {}
    missing = _MissingDependencies()
    _add_all_dependencies(deps, missing, all_collections)
    assert deps == {}  # pylint: disable=use-implicit-booleaness-not-comparison
    assert missing.is_empty()

    # Collection without deps
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.bar",
        ]
    }
    missing = _MissingDependencies()
    _add_all_dependencies(deps, missing, all_collections)
    assert deps.keys() == {"foo.bar"}
    assert missing.is_empty()

    # Collection with single dep
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.bam",
        ]
    }
    missing = _MissingDependencies()
    _add_all_dependencies(deps, missing, all_collections)
    assert deps.keys() == {"foo.bar", "foo.bam"}
    assert missing.is_empty()

    # Collection with two deps
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.baz",
        ]
    }
    missing = _MissingDependencies()
    _add_all_dependencies(deps, missing, all_collections)
    assert deps.keys() == {"foo.bar", "foo.bam", "foo.baz"}
    assert missing.is_empty()

    # Collection with dependency chain where leaf is already there
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.bar",
            "foo.foo",
        ]
    }
    missing = _MissingDependencies()
    _add_all_dependencies(deps, missing, all_collections)
    assert deps.keys() == {"foo.bar", "foo.bam", "foo.foo"}
    assert missing.is_empty()

    # Missing collection
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.error",
        ]
    }
    missing = _MissingDependencies()
    _add_all_dependencies(deps, missing, all_collections)
    assert not missing.is_empty()
    assert missing.get_missing_names() == ["foo.does_not_exist"]


def test__extract_collections_from_extra_deps_file_special(tmp_path: Path) -> None:
    # pylint: disable-next=use-implicit-booleaness-not-comparison
    assert _extract_collections_from_extra_deps_file(tmp_path / "does-not-exist") == []

    dir = tmp_path / "test1"
    dir.mkdir()
    with pytest.raises(
        ValueError,
        match="Error while loading collection dependency file.*Is a directory:",
    ):
        _extract_collections_from_extra_deps_file(dir)


EXTRACT_COLLECTIONS_FROM_EXTRA_DEPS_FILE_DATA: list[tuple[str, list[str]]] = [
    (
        r"""
collections: []
""",
        [],
    ),
    (
        r"""
collections:
    - foo
    - name: bar
""",
        ["foo", "bar"],
    ),
    (
        # Not exactly legal, but works:
        r"""
collections:
    foo: bar
    baz:
""",
        ["foo", "baz"],
    ),
]


@pytest.mark.parametrize(
    "content, expected_result",
    EXTRACT_COLLECTIONS_FROM_EXTRA_DEPS_FILE_DATA,
)
def test__extract_collections_from_extra_deps_file(
    content: str, expected_result: list[str], tmp_path: Path
) -> None:
    file = tmp_path / "test1"
    file.write_text(content)
    assert _extract_collections_from_extra_deps_file(file) == expected_result


EXTRACT_COLLECTIONS_FROM_EXTRA_DEPS_FILE_FAIL_DATA: list[tuple[str, str]] = [
    (
        r"""
collections:
    foo: bar
    23: baz
""",
        "Collection entry #2 must be a string or dictionary",
    ),
    (
        r"""
collections:
    - 42
""",
        "Collection entry #1 must be a string or dictionary",
    ),
    (
        r"""
collections:
    - name:
""",
        "Collection entry #1 does not have a 'name' field of type string",
    ),
    (
        r"""
collections:
    - bar: baz
""",
        "Collection entry #1 does not have a 'name' field of type string",
    ),
]


@pytest.mark.parametrize(
    "content, expected_match",
    EXTRACT_COLLECTIONS_FROM_EXTRA_DEPS_FILE_FAIL_DATA,
)
def test__extract_collections_from_extra_deps_file_fail(
    content: str, expected_match: str, tmp_path: Path
) -> None:
    file = tmp_path / "test1"
    file.write_text(content)
    with pytest.raises(ValueError, match=expected_match):
        _extract_collections_from_extra_deps_file(file)
