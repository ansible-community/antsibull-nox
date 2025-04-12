# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

"""
Tests for the collection module
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import pytest
from antsibull_fileutils.yaml import load_yaml_file, store_yaml_file

from antsibull_nox.collection import (
    CollectionData,
    Runner,
    force_collection_version,
    load_collection_data_from_disk,
)
from antsibull_nox.collection.install import (
    _add_all_dependencies,
    _extract_collections_from_extra_deps_file,
)
from antsibull_nox.collection.search import (
    CollectionList,
    _fs_list_local_collections,
    _galaxy_list_collections,
    get_collection_list,
)

from .utils import chdir


def create_once_runner(args: list[str], stdout: bytes, stderr: bytes = b"") -> Runner:
    call_counter = [0]

    def runner(call_args: list[str]) -> tuple[bytes, bytes]:
        assert call_counter[0] == 0
        assert call_args == args
        call_counter[0] += 1
        return stdout, stderr

    return runner


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
    deps = {}
    _add_all_dependencies(deps, all_collections)
    assert deps == {}  # pylint: disable=use-implicit-booleaness-not-comparison

    # Collection without deps
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.bar",
        ]
    }
    _add_all_dependencies(deps, all_collections)
    assert deps.keys() == {"foo.bar"}

    # Collection with single dep
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.bam",
        ]
    }
    _add_all_dependencies(deps, all_collections)
    assert deps.keys() == {"foo.bar", "foo.bam"}

    # Collection with two deps
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.baz",
        ]
    }
    _add_all_dependencies(deps, all_collections)
    assert deps.keys() == {"foo.bar", "foo.bam", "foo.baz"}

    # Collection with dependency chain where leaf is already there
    deps = {
        name: all_collections.find(name)
        for name in [
            "foo.bar",
            "foo.foo",
        ]
    }
    _add_all_dependencies(deps, all_collections)
    assert deps.keys() == {"foo.bar", "foo.bam", "foo.foo"}

    # Missing collection
    with pytest.raises(
        ValueError,
        match="^Cannot find collection foo.does_not_exist, a dependency of foo.error!$",
    ):
        deps = {
            name: all_collections.find(name)
            for name in [
                "foo.error",
            ]
        }
        _add_all_dependencies(deps, all_collections)


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


def create_collection(
    path: Path,
    *,
    namespace: str,
    name: str,
    version: str | None = None,
    dependencies: dict[str, str] | None = None,
) -> None:
    data = {
        "namespace": namespace,
        "name": name,
    }
    if version is not None:
        data["version"] = version
    if dependencies is not None:
        data["dependencies"] = dependencies
    path.mkdir(parents=True, exist_ok=True)
    store_yaml_file(path / "galaxy.yml", data)


def create_collection_w_dir(
    root: Path,
    *,
    namespace: str,
    name: str,
    version: str | None = None,
    dependencies: dict[str, str] | None = None,
) -> Path:
    path = root / namespace / name
    create_collection(
        path=path,
        namespace=namespace,
        name=name,
        version=version,
        dependencies=dependencies,
    )
    return path


def create_collection_w_shallow_dir(
    root: Path,
    *,
    directory_override: str | None = None,
    namespace: str,
    name: str,
    version: str | None = None,
    dependencies: dict[str, str] | None = None,
) -> Path:
    path = root / (directory_override or f"{namespace}.{name}")
    create_collection(
        path=path,
        namespace=namespace,
        name=name,
        version=version,
        dependencies=dependencies,
    )
    return path


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
    (root / "empty").mkdir()
    (root / "blubb").mkdir()
    (root / "blubb" / "foo").write_text("nothing")
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
            .replace("<ROOT3>", str(root3)),
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
                    stdout="{",
                )
            )
        )


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


def test_get_collection_list(tmp_path) -> None:
    root1 = tmp_path / "root-1" / "ansible_collections"
    root2 = tmp_path / "root-2" / "ansible_collections"
    root3 = tmp_path / "root-3" / "ansible_collections"

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
        .replace("<ROOT3>", str(root3)),
    )

    with chdir(root3 / "foo" / "bar"):
        get_collection_list.cache_clear()  # added by @functools.cache
        result = get_collection_list(runner)

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


FORCE_COLLECTION_VERSION_DATA: list[tuple[str, str, bool, dict[str, t.Any]]] = [
    (
        r"""name: foo""",
        "1.2.3",
        True,
        {
            "name": "foo",
            "version": "1.2.3",
        },
    ),
    (
        r"""version: []""",
        "1.2.3",
        True,
        {
            "version": "1.2.3",
        },
    ),
    (
        r"""version: 1.2.2""",
        "1.2.3",
        True,
        {
            "version": "1.2.3",
        },
    ),
    (
        r"""version: 1.2.3""",
        "1.2.3",
        False,
        {
            "version": "1.2.3",
        },
    ),
    (
        r"""
name: boo
namespace: foo
version: null""",
        "1.2.3",
        True,
        {
            "name": "boo",
            "namespace": "foo",
            "version": "1.2.3",
        },
    ),
]


@pytest.mark.parametrize(
    "content, version, expected_result, expected_content",
    FORCE_COLLECTION_VERSION_DATA,
)
def test_force_collection_version(
    content: str,
    version: str,
    expected_result: bool,
    expected_content: dict[str, t.Any],
    tmp_path: Path,
) -> None:
    file = tmp_path / "galaxy.yml"
    file.write_text(content)
    result = force_collection_version(tmp_path, version=version)
    assert result == expected_result
    assert load_yaml_file(file) == expected_content


FORCE_COLLECTION_VERSION_FAIL_DATA: list[tuple[str, str, str]] = [
    (
        r"""{""",
        "1.2.3",
        "^Cannot parse .*/galaxy.yml: ",
    ),
]


@pytest.mark.parametrize(
    "content, version, expected_match",
    FORCE_COLLECTION_VERSION_FAIL_DATA,
)
def test_force_collection_version_fail(
    content: str, version: str, expected_match: str, tmp_path: Path
) -> None:
    file = tmp_path / "galaxy.yml"
    file.write_text(content)
    with pytest.raises(ValueError, match=expected_match):
        force_collection_version(tmp_path, version=version)
