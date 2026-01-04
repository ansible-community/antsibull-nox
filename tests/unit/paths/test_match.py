# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

# pylint: disable=missing-function-docstring

"""
Test path matchers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from antsibull_nox.paths.match import FileCollector, _FileSet, _FileTree

from ..utils import chdir


def test_FileSet() -> None:
    fs1 = _FileSet.create([Path("foo")])
    fs2 = _FileSet.create([Path("bar")])
    fs3 = _FileSet.create([Path("foo"), Path("bar")])

    fs = _FileSet.create_from_split(split_files=[("foo",), ("foo",)])
    assert fs == fs1

    assert fs3.subset({("foo",)}) == fs1
    assert fs3.subset({("bar",)}) == fs2

    fs = fs1.clone()
    fs.merge_set(fs1)
    assert fs == fs1

    fs = fs1.clone()
    fs.merge_set(fs2)
    assert fs == fs3

    fs = fs1.clone()
    fs.merge_paths(paths=[Path("foo")])
    assert fs == fs1

    fs = fs1.clone()
    fs.merge_paths(paths=[Path("bar")])
    assert fs == fs3


def test_FileTree() -> None:
    ft = _FileTree.create_from_paths(
        [
            Path("foo/bar"),
            Path("foo"),
            Path("foo/bam"),
            Path("bam/baz/bar"),
        ],
        keep_pruned=True,
    )
    assert sorted(ft.iterate()) == [("bam", "baz", "bar"), ("foo",)]

    assert ft.has_or_has_children(())
    assert not ft.has_or_has_children(("bar",))
    assert ft.has_or_has_children(("foo",))
    assert not ft.has_or_has_children(("foo", "bar"))
    assert not ft.has_or_has_children(("foo", "baz"))
    assert ft.has_or_has_children(("bam",))
    assert not ft.has_or_has_children(("bam", "bar"))
    assert ft.has_or_has_children(("bam", "baz"))
    assert ft.has_or_has_children(("bam", "baz", "bar"))
    assert not ft.has_or_has_children(("bam", "baz", "bar", "boom"))

    assert not ft.has_or_is_child(())
    assert not ft.has_or_is_child(("bar",))
    assert ft.has_or_is_child(("foo",))
    assert ft.has_or_is_child(("foo", "bar"))
    assert ft.has_or_is_child(("foo", "baz"))
    assert not ft.has_or_is_child(("bam",))
    assert not ft.has_or_is_child(("bam", "bar"))
    assert not ft.has_or_is_child(("bam", "baz"))
    assert ft.has_or_is_child(("bam", "baz", "bar"))
    assert ft.has_or_is_child(("bam", "baz", "bar", "boom"))

    assert sorted(ft.iterate(prefix=("foo", "foo"))) == []

    ft = _FileTree.create_from_paths(
        [
            Path("foo/bar"),
            Path("foo"),
            Path("foo/bam"),
            Path("."),
        ],
        keep_pruned=False,
    )
    assert sorted(ft.iterate()) == [(), ("foo",), ("foo", "bam"), ("foo", "bar")]


@pytest.fixture(name="path_structure", scope="module")
def create_path_structure(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("path-structure")
    (root / "a").write_text("")
    (root / "b").write_text("")

    c = root / "c"
    c.mkdir()
    (c / "ca").write_text("")
    (c / "cb").write_text("")
    cpycache = c / "__pycache__"
    cpycache.mkdir()
    (cpycache / "x").write_text("")
    (c / "ca").write_text("")
    (c / "cb").write_text("")
    cc = c / "cc"
    cc.mkdir()
    (cc / "cca").write_text("")
    (cc / "ccb").write_text("")
    cd = c / "cd"
    cd.mkdir()
    (cd / "cda").write_text("")
    (cd / "cdb").write_text("")

    d = root / "d"
    d.mkdir()
    (d / "da").write_text("")
    (d / "db").write_text("")
    dc = d / "dc"
    dc.mkdir()
    (dc / "dca").write_text("")
    (dc / "dcb").write_text("")
    dd = d / "dd"
    dd.mkdir()
    (dd / "dda").write_text("")
    (dd / "ddb").write_text("")

    e = root / "e"
    e.mkdir()
    (e / "ea.py").write_text("")
    (e / "eb.txt").write_text("")
    ec = e / "ec"
    ec.mkdir()
    (ec / "eca.py").write_text("")
    (ec / "ecb.txt").write_text("")
    ed = e / "ed.py"
    ed.mkdir()
    (ed / "eda.py").write_text("")
    (ed / "edb.txt").write_text("")
    ee = e / "ee.txt"
    ee.mkdir()
    (ee / "eea.py").write_text("")
    (ee / "eeb.txt").write_text("")

    return root


TEST_GET_PATHS: list[tuple[list[str], list[str]]] = [
    (
        ["."],
        ["."],
    ),
    (
        [".", "."],
        ["."],
    ),
    (
        ["foo", "bar", "baz", "bar/"],
        ["foo", "bar", "baz"],
    ),
]


@pytest.mark.parametrize(
    "start_paths, expected_paths",
    TEST_GET_PATHS,
)
def test_get_paths(
    start_paths: list[str],
    expected_paths: list[str],
) -> None:
    fc = FileCollector(paths=[Path(path) for path in start_paths])
    result = [str(path) for path in fc.get_paths()]
    assert result == expected_paths

    assert fc.clone().get_paths() == fc.get_paths()


TEST_GET_EXISTING: list[tuple[list[str], list[str]]] = [
    (
        ["."],
        ["."],
    ),
    (
        ["c/cd/cda"],
        ["c/cd/cda"],
    ),
    (
        ["foo", "bar", "baz", "a", "c", "c/a", "c/ca"],
        ["a", "c", "c/ca"],
    ),
]


@pytest.mark.parametrize(
    "start_paths, expected_paths",
    TEST_GET_EXISTING,
)
def test_get_existing(
    start_paths: list[str],
    expected_paths: list[str],
    path_structure: Path,
) -> None:
    with chdir(path_structure):
        fc = FileCollector(paths=[Path(path) for path in start_paths])
        result = [str(path) for path in fc.get_existing()]
        assert result == expected_paths


TEST_RESTRICT: list[tuple[list[str], list[str], list[str]]] = [
    (
        ["."],
        ["."],
        ["."],
    ),
    (
        ["."],
        ["foo"],
        ["foo"],
    ),
    (
        ["foo/bar"],
        ["foo"],
        ["foo/bar"],
    ),
    (
        ["bam", "bam/foo/bar", "bar"],
        ["bam/foo"],
        ["bam/foo", "bam/foo/bar"],
    ),
    (
        ["."],
        ["foo/bar", "foo", "foo/bam"],
        ["foo"],
    ),
    (
        ["foo", "bar"],
        ["foo", "bar/baz", "bar/bam", "bam"],
        ["bar/bam", "bar/baz", "foo"],
    ),
    (
        ["foo/bam", "foo/bar"],
        ["foo"],
        ["foo/bam", "foo/bar"],
    ),
    (
        ["foo"],
        ["foo/bam", "foo/bar"],
        ["foo/bam", "foo/bar"],
    ),
    (
        ["foo"],
        ["foo"],
        ["foo"],
    ),
]


@pytest.mark.parametrize(
    "start_paths, restrict_paths, expected_paths",
    TEST_RESTRICT,
)
def test_restrict(
    start_paths: list[str],
    restrict_paths: list[str],
    expected_paths: list[str],
) -> None:
    fc = FileCollector(paths=[Path(path) for path in start_paths])
    fc.restrict(paths=[Path(path) for path in restrict_paths])
    result = sorted(str(path) for path in fc.get_paths())
    assert result == expected_paths

    # Alternative way
    fc1 = FileCollector(paths=[Path(path) for path in start_paths])
    fc2 = FileCollector(paths=[Path(path) for path in restrict_paths])
    fc1.restrict(paths=fc2)
    result = sorted(str(path) for path in fc1.get_paths())
    assert result == expected_paths


TEST_REMOVE: list[tuple[list[str], list[str], list[str] | None, list[str]]] = [
    (
        ["c"],
        ["."],
        None,
        [],
    ),
    (
        ["a", "b", "c"],
        ["d"],
        None,
        ["a", "b", "c"],
    ),
    (
        ["a", "b", "c", "d", "d/da", "d/db", "d/dc/dca"],
        ["c/a", "d"],
        None,
        ["a", "b", "c/ca", "c/cb", "c/cc", "c/cd"],
    ),
    (
        ["a", "b", "c", "d", "d/da", "d/db", "d/dc/dca"],
        ["c/ca", "c/cc", "c/cd/cda", "d/dc"],
        None,
        ["a", "b", "c/cb", "c/cd/cdb", "d/da", "d/db", "d/dd"],
    ),
    (
        ["d"],
        ["d/da", "d/dc"],
        None,
        ["d/db", "d/dd"],
    ),
    (
        ["e"],
        ["e/x"],
        ["py", ".txt"],
        ["e/ea.py", "e/ec", "e/ed.py", "e/ee.txt"],
    ),
]


@pytest.mark.parametrize(
    "start_paths, remove_paths, extensions, expected_paths",
    TEST_REMOVE,
)
def test_remove(
    start_paths: list[str],
    remove_paths: list[str],
    extensions: list[str] | None,
    expected_paths: list[str],
    path_structure: Path,
) -> None:
    with chdir(path_structure):
        fc = FileCollector(paths=[Path(path) for path in start_paths])
        fc.remove(paths=[Path(path) for path in remove_paths], extensions=extensions)
        result = sorted(str(path) for path in fc.get_paths())
        assert result == expected_paths


TEST_CREATE: list[tuple[list[str], bool, list[str]]] = [
    (
        ["c", "moo"],
        False,
        ["c", "moo"],
    ),
    (
        ["*/?c", "*/*fff", "e", "moo"],
        True,
        ["c/cc", "d/dc", "e", "moo"],
    ),
    (
        ["."],
        True,
        ["."],
    ),
]


@pytest.mark.parametrize(
    "sources, glob, expected_paths",
    TEST_CREATE,
)
def test_create(
    sources: list[str],
    glob: bool,
    expected_paths: list[str],
    path_structure: Path,
) -> None:
    with chdir(path_structure):
        fc = FileCollector.create(sources, glob=glob)
        result = sorted(str(path) for path in fc.get_paths())
        assert result == expected_paths
