# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

"""
Tests for the collection.search module
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import pytest

from antsibull_nox.collection.data import (
    CollectionData,
)
from antsibull_nox.collection.search import (
    _COLLECTION_LIST,
    _fs_list_local_collections,
    _galaxy_list_collections,
    get_collection_list,
    load_collection_data_from_disk,
)

from ..utils import chdir
from .utils import (
    create_collection_w_dir,
    create_collection_w_shallow_dir,
    create_once_runner,
)


def test__fs_list_local_collections(tmp_path: Path) -> None:
    # Case 1: regular ansible_collections tree
    root = tmp_path / "test-1" / "ansible_collections"
    root.mkdir(parents=True)
    foo_bar = create_collection_w_dir(root, namespace="foo", name="bar")
    foo_bam = create_collection_w_dir(
        root,
        namespace="foo",
        name="bam",
        dependencies={"foo.bar": ">= 1.0.0", "community.baz": "*"},
    )
    community_baz = create_collection_w_dir(
        root, namespace="community", name="baz", dependencies={"community.foo": "*"}
    )
    (root / "blah").write_text("nothing")
    (root / "blahsym").symlink_to("blah")
    (root / "empty").mkdir()
    (root / "blubb").mkdir()
    (root / "blubb" / "foo").write_text("nothing")
    (root / "blubb" / "foosym").symlink_to("foo")
    (root / "community" / "foo").write_text("nothing")
    (root / "community" / "bam").mkdir()
    with chdir(foo_bar):
        result = sorted(_fs_list_local_collections(), key=lambda c: c.full_name)
    assert result == [
        CollectionData.create(
            collections_root_path=root,
            path=community_baz,
            full_name="community.baz",
            dependencies={"community.foo": "*"},
        ),
        CollectionData.create(
            collections_root_path=root,
            path=foo_bam,
            full_name="foo.bam",
            dependencies={"foo.bar": ">= 1.0.0", "community.baz": "*"},
        ),
        CollectionData.create(
            collections_root_path=root, path=foo_bar, full_name="foo.bar", current=True
        ),
    ]

    # Case 2: repositories checked out as <namespace>.<name>
    root = tmp_path / "test-2"
    root.mkdir(parents=True)
    foo_bar = create_collection_w_shallow_dir(root, namespace="foo", name="bar")
    foo_bam = create_collection_w_shallow_dir(
        root,
        namespace="foo",
        name="bam",
        dependencies={"foo.bar": ">= 1.0.0", "community.baz": "*"},
    )
    create_collection_w_shallow_dir(
        root, namespace="bar", name="baz", directory_override="bar.bar"
    )
    community_baz = create_collection_w_shallow_dir(
        root, namespace="community", name="baz", dependencies={"community.foo": "*"}
    )
    (root / "blah").write_text("nothing")
    (root / "empty").mkdir()
    (root / "foo.baz").mkdir()
    (root / "1.2").mkdir()
    with chdir(foo_bar):
        result = sorted(_fs_list_local_collections(), key=lambda c: c.full_name)
    assert result == [
        CollectionData.create(
            path=community_baz,
            full_name="community.baz",
            dependencies={"community.foo": "*"},
        ),
        CollectionData.create(
            path=foo_bam,
            full_name="foo.bam",
            dependencies={"foo.bar": ">= 1.0.0", "community.baz": "*"},
        ),
        CollectionData.create(path=foo_bar, full_name="foo.bar", current=True),
    ]

    # Case 3: looks like ansible_collection tree on first glance, but it's not
    root = tmp_path / "test-3" / "ansible_collections" / "foo"
    root.mkdir(parents=True)
    foo_bar = create_collection_w_shallow_dir(root, namespace="foo", name="bar")
    foo_bam = create_collection_w_shallow_dir(
        root,
        namespace="foo",
        name="bam",
        dependencies={"foo.bar": ">= 1.0.0", "community.baz": "*"},
    )
    create_collection_w_shallow_dir(
        root, namespace="bar", name="baz", directory_override="bar.bar"
    )
    (root / "foo.baz").mkdir()
    with chdir(foo_bam):
        result = sorted(_fs_list_local_collections(), key=lambda c: c.full_name)
    assert result == [
        CollectionData.create(
            path=foo_bam,
            full_name="foo.bam",
            dependencies={"foo.bar": ">= 1.0.0", "community.baz": "*"},
            current=True,
        ),
        CollectionData.create(
            path=foo_bar,
            full_name="foo.bar",
        ),
    ]

    # Failure while loading current collection
    root = tmp_path / "test-4"
    root.mkdir(parents=True)
    cwd = root / "something"
    cwd.mkdir()
    with chdir(cwd):
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*:"
                " Cannot find galaxy.yml or MANIFEST.json in "
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "MANIFEST.json").write_text("foo")
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "/something: Cannot parse .*something/MANIFEST.json: "
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "MANIFEST.json").write_text("{}")
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "/something/MANIFEST.json does not contain collection_info$"
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "MANIFEST.json").write_text('{"collection_info": "meh"}')
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "/something/MANIFEST.json does not contain collection_info$"
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "MANIFEST.json").write_text('{"collection_info": {}}')
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "/something/MANIFEST.json does not contain a namespace$"
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "galaxy.yml").write_text("{")
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "/something: Cannot parse .*something/galaxy.yml: "
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "galaxy.yml").write_text("[]")
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "/something: .*something/galaxy.yml is not a dictionary"
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "galaxy.yml").write_text("namespace: whatever")
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "something/galaxy.yml does not contain a name$"
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "galaxy.yml").write_text("namespace: 42")
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "something/galaxy.yml does not contain a namespace$"
            ),
        ):
            list(_fs_list_local_collections())

        (cwd / "galaxy.yml").write_text(
            "namespace: foo\nname: bar\ndependencies: [foo]"
        )
        with pytest.raises(
            ValueError,
            match=(
                "^Cannot load current collection's info from.*"
                "something/galaxy.yml's dependencies is not a mapping$"
            ),
        ):
            list(_fs_list_local_collections())


GALAXY_LIST_COLLECTIONS_DATA: list[tuple[str, list[dict[str, t.Any]]]] = [
    (
        r"""
{}
""",
        [],
    ),
    (
        r"""
{
    "/": {}
}
""",
        [],
    ),
    (
        r"""
{
    "<ROOT1>": {
        "foo.bar": {}
    }
}
""",
        [
            {
                "root": 1,
                "full_name": "foo.bar",
            },
            {
                "root": 1,
                "full_name": "foo.bam",
                "hide": True,
            },
        ],
    ),
    (
        r"""
{
    "<ROOT1>": {
        "foo.bar": {},
        "foo.bam": {}
    },
    "<ROOT2>": {
        "foo.bam": {},
        "foo.baz": {}
    },
    "/does-not-exist": {
        "foo.bar": {}
    }
}
""",
        [
            {
                "root": 1,
                "full_name": "foo.bar",
            },
            {
                "root": 1,
                "full_name": "foo.bam",
            },
            {
                "root": 1,
                "full_name": "foo.baz",
                "hide": True,
            },
            {
                "root": 2,
                "full_name": "foo.bam",
                "version": "1.0.0",
            },
            {"root": 2, "full_name": "foo.baz", "dependencies": {"foo.bar": "*"}},
        ],
    ),
]


@pytest.mark.parametrize(
    "content, expected_result",
    GALAXY_LIST_COLLECTIONS_DATA,
)
def test__galaxy_list_collections(
    tmp_path: Path, content: str, expected_result: list[dict[str, t.Any]]
) -> None:
    root1 = tmp_path / "root-1" / "ansible_collections"
    root2 = tmp_path / "root-2" / "ansible_collections"
    root3 = tmp_path / "root-3" / "ansible_collections"

    def create(c: dict[str, t.Any]) -> tuple[CollectionData, bool]:
        root: Path = {
            1: root1,
            2: root2,
            3: root3,
        }[c.pop("root")]
        full_name: str = c.pop("full_name")
        hide: bool = c.pop("hide", False)
        namespace, name = full_name.split(".", 1)
        path = create_collection_w_dir(root, namespace=namespace, name=name, **c)
        return (
            CollectionData.create(
                collections_root_path=root,
                path=path,
                full_name=full_name,
                **c,
            ),
            hide,
        )

    expected_res_with_hide = [create(c) for c in expected_result]
    expected_res = sorted(
        [c for c, h in expected_res_with_hide if not h], key=lambda c: c.full_name
    )

    result = _galaxy_list_collections(
        create_once_runner(
            ["ansible-galaxy", "collection", "list", "--format", "json"],
            stdout=content.replace("<ROOT1>", str(root1))
            .replace("<ROOT2>", str(root2))
            .replace("<ROOT3>", str(root3))
            .encode("utf-8"),
            expect_check=False,
        )
    )
    res = sorted(result, key=lambda c: c.full_name)
    assert res == expected_res


def test__galaxy_list_collections_fail() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "^Error while loading collection list: "
            "Expecting property name enclosed in double quotes: "
        ),
    ):
        list(
            _galaxy_list_collections(
                create_once_runner(
                    ["ansible-galaxy", "collection", "list", "--format", "json"],
                    stdout=b"{",
                    expect_check=False,
                ),
            )
        )

    with pytest.raises(
        ValueError,
        match=(
            "^Error while loading collection list: "
            "Unexpected return code 123 when listing collections. Standard error output: foo$"
        ),
    ):
        list(
            _galaxy_list_collections(
                create_once_runner(
                    ["ansible-galaxy", "collection", "list", "--format", "json"],
                    stdout=b"bar",
                    stderr=b"foo",
                    expect_check=False,
                    rc=123,
                ),
            )
        )


def test_get_collection_list(tmp_path) -> None:
    root1 = tmp_path / "root-1" / "ansible_collections"
    root2 = tmp_path / "root-2" / "ansible_collections"
    root3 = tmp_path / "root-3" / "ansible_collections"
    empty = tmp_path / "empty"

    create_collection_w_dir(root1, namespace="foo", name="bar", version="1.0.0")
    root1_foo_bam = create_collection_w_dir(
        root1, namespace="foo", name="bam", dependencies={"foo.bar": ">= 1.0.0"}
    )
    create_collection_w_dir(root2, namespace="foo", name="bam", version="0.1.0")
    root3_foo_bar = create_collection_w_dir(root3, namespace="foo", name="bar")

    content = r"""
{
    "<ROOT1>": {
        "foo.bar": {},
        "foo.bam": {}
    },
    "<ROOT2>": {
        "foo.bam": {},
        "foo.baz": {}
    },
    "<ROOT3>": {
        "foo.bar": {}
    }
}
"""

    runner = create_once_runner(
        ["ansible-galaxy", "collection", "list", "--format", "json"],
        stdout=content.replace("<ROOT1>", str(root1))
        .replace("<ROOT2>", str(root2))
        .replace("<ROOT3>", str(root3))
        .encode("utf-8"),
        expect_check=False,
    )

    with chdir(root3 / "foo" / "bar"):
        _COLLECTION_LIST.clear()
        assert _COLLECTION_LIST.get_cached() is None
        result = get_collection_list(
            runner=runner, global_cache_dir=empty, ansible_core_version="devel"
        )
        cl = _COLLECTION_LIST.get_cached()
        assert cl is not None
        result_2 = get_collection_list(
            runner=runner, global_cache_dir=empty, ansible_core_version="devel"
        )
        assert _COLLECTION_LIST.get_cached() is cl

        with pytest.raises(
            ValueError, match="^Setup mismatch: global cache dir cannot be both "
        ):
            get_collection_list(
                runner=runner, global_cache_dir=tmp_path, ansible_core_version="devel"
            )

    assert result.collections == sorted(
        [
            CollectionData.create(
                collections_root_path=root1,
                path=root1_foo_bam,
                full_name="foo.bam",
                dependencies={"foo.bar": ">= 1.0.0"},
            ),
            CollectionData.create(
                collections_root_path=root3,
                path=root3_foo_bar,
                full_name="foo.bar",
                current=True,
            ),
        ],
        key=lambda c: c.full_name,
    )

    assert result == cl
    assert result == result_2


LOAD_COLLECTION_DATA_FROM_DISK_DATA: list[
    tuple[str, str, dict[str, t.Any], dict[str, t.Any]]
] = [
    (
        "galaxy.yml",
        r"""
namespace: foo
name: bar
version: 1.0.0
dependencies: {}
""",
        {},
        {
            "full_name": "foo.bar",
            "version": "1.0.0",
        },
    ),
    (
        "galaxy.yml",
        r"""
namespace: foo
name: bar
version: 1.0.0
dependencies:
    foo.bam: "*"
""",
        {
            "namespace": "foo",
            "name": "bar",
            "current": True,
            "root": "/",
        },
        {
            "full_name": "foo.bar",
            "version": "1.0.0",
            "dependencies": {"foo.bam": "*"},
            "current": True,
            "collections_root_path": "/",
        },
    ),
]


@pytest.mark.parametrize(
    "filename, content, paras, expected_result",
    LOAD_COLLECTION_DATA_FROM_DISK_DATA,
)
def test_load_collection_data_from_disk(
    filename: str,
    content: str,
    paras: dict[str, t.Any],
    expected_result: dict[str, t.Any],
    tmp_path: Path,
) -> None:
    (tmp_path / filename).write_text(content)
    res = load_collection_data_from_disk(tmp_path, **paras)
    expected_res = CollectionData.create(path=tmp_path, **expected_result)
    assert res == expected_res


LOAD_COLLECTION_DATA_FROM_DISK_FAIL_DATA: list[
    tuple[str, str, dict[str, t.Any], str]
] = [
    (
        "galaxy.yml",
        r"""
name: foo.bar
""",
        {},
        "/galaxy.yml does not contain a namespace$",
    ),
    (
        "galaxy.yml",
        r"""
namespace: foo
name: bar
version: 1.0.0
""",
        {
            "namespace": "foo",
            "name": "bam",
        },
        "/galaxy.yml contains name 'bar', but was hoping for 'bam'$",
    ),
    (
        "galaxy.yml",
        r"""
namespace: foo
name: bar
version: null
""",
        {
            "namespace": "fuu",
            "name": "bar",
        },
        "/galaxy.yml contains namespace 'foo', but was hoping for 'fuu'$",
    ),
    (
        "MANIFEST.json",
        "{}",
        {"accept_manifest": False},
        "^Cannot find galaxy.yml in ",
    ),
]


@pytest.mark.parametrize(
    "filename, content, paras, expected_match",
    LOAD_COLLECTION_DATA_FROM_DISK_FAIL_DATA,
)
def test_load_collection_data_from_disk_fail(
    filename: str,
    content: str,
    paras: dict[str, t.Any],
    expected_match: str,
    tmp_path: Path,
) -> None:
    (tmp_path / filename).write_text(content)
    with pytest.raises(ValueError, match=expected_match):
        load_collection_data_from_disk(tmp_path, **paras)
