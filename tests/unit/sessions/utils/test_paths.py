# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

# pylint: disable=missing-function-docstring

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from antsibull_nox.config import CONFIG_FILENAME
from antsibull_nox.python.python_dependencies import PythonDependencyInfo
from antsibull_nox.sessions.utils.paths import (
    _massage_paths_to_trigger_full_build,
    add_python_deps,
)


def test_add_python_deps() -> None:
    cwd = Path.cwd()

    foo_py = cwd / "foo.py"
    bar_init_py = cwd / "bar" / "__init__.py"
    bar_bam_py = cwd / "bar" / "bam.py"
    bar_baz_py = cwd / "bar" / "baz.py"
    bam_py = cwd / "bam.py"
    boo_py = (cwd / ".." / "boo.py").resolve()

    foo = ("foo",)
    bar = ("bar",)
    bar_bam = ("bar", "bam")
    bar_baz = ("bar", "baz")
    bam = ("bam",)
    boo = ("boo",)

    with patch(
        "antsibull_nox.sessions.utils.paths.get_python_dependency_info",
        return_value=PythonDependencyInfo(
            file_to_module_path={},
            module_path_to_file={},
            file_to_imported_modules={},
            file_to_imported_by_modules={},
        ),
    ):
        files: list[Path] = []
        add_python_deps(files, forward=True, cwd=cwd)
        assert files == []

        files = [Path("foo.py"), bar_bam_py]
        add_python_deps(files, forward=True, cwd=cwd)
        assert files == [Path("foo.py"), bar_bam_py]

        files = [Path("foo.py"), bar_bam_py]
        add_python_deps(files, forward=False, cwd=cwd)
        assert files == [Path("foo.py"), bar_bam_py]

    with patch(
        "antsibull_nox.sessions.utils.paths.get_python_dependency_info",
        return_value=PythonDependencyInfo(
            file_to_module_path={
                foo_py: foo,
                bar_init_py: bar,
                bar_bam_py: bar_bam,
                bar_baz_py: bar_baz,
                bam_py: bam,
                boo_py: boo,
            },
            module_path_to_file={
                foo: foo_py,
                bar: bar_init_py,
                bar_bam: bar_bam_py,
                bar_baz: bar_baz_py,
                bam: bam_py,
                boo: boo_py,
            },
            file_to_imported_modules={
                foo_py: (frozenset([bar]), frozenset([bar_init_py])),
                bar_init_py: (frozenset([]), frozenset([])),
                bar_bam_py: (
                    frozenset([bar, bar_baz]),
                    frozenset([bar_init_py, bar_baz_py]),
                ),
                bar_baz_py: (frozenset([bar, bam]), frozenset([bar_init_py, bam_py])),
                bam_py: (frozenset([boo]), frozenset([boo_py])),
                boo_py: (frozenset([foo]), frozenset([foo_py])),
            },
            file_to_imported_by_modules={
                foo_py: (frozenset([boo]), frozenset([boo_py])),
                bar_init_py: (
                    frozenset([foo, bar_bam, bar_baz]),
                    frozenset([foo_py, bar_bam_py, bar_baz_py]),
                ),
                bar_bam_py: (frozenset([]), frozenset([])),
                bar_baz_py: (frozenset([bar_bam]), frozenset([bar_bam_py])),
                bam_py: (frozenset([bar_baz]), frozenset([bar_baz_py])),
                boo_py: (frozenset([bam]), frozenset([bam_py])),
            },
        ),
    ):
        files = []
        add_python_deps(files, forward=True, cwd=cwd)
        assert files == []

        files = [Path("foo.py"), bar_bam_py]
        add_python_deps(files, forward=True, cwd=cwd)
        assert set(files) == {
            Path("foo.py"),
            bar_bam_py,
            Path("bar") / "__init__.py",
            Path("bar") / "baz.py",
            Path("bam.py"),
        }

        files = [Path("foo.py"), bar_bam_py]
        add_python_deps(files, forward=False, cwd=cwd)
        assert set(files) == {
            Path("foo.py"),
            bar_bam_py,
            Path("bam.py"),
            Path("bar") / "baz.py",
        }

        files = [
            Path("bar") / "bam.py",
        ]
        add_python_deps(files, forward=True, cwd=cwd)
        assert set(files) == {
            Path("foo.py"),
            Path("bar") / "__init__.py",
            Path("bar") / "baz.py",
            Path("bar") / "bam.py",
            Path("bam.py"),
        }

        files = [
            Path("bar") / "__init__.py",
        ]
        add_python_deps(files, forward=False, cwd=cwd)
        assert set(files) == {
            Path("foo.py"),
            Path("bar") / "__init__.py",
            Path("bar") / "baz.py",
            Path("bar") / "bam.py",
            Path("bam.py"),
        }


def test__massage_paths_to_trigger_full_build() -> None:
    # (paths_to_trigger_full_build: Sequence[Path] | None) -> list[Path]:
    assert _massage_paths_to_trigger_full_build(None) == [Path(CONFIG_FILENAME)]
    assert _massage_paths_to_trigger_full_build([]) == [Path(CONFIG_FILENAME)]
    assert _massage_paths_to_trigger_full_build([Path("foo")]) == [
        Path("foo"),
        Path(CONFIG_FILENAME),
    ]
    assert _massage_paths_to_trigger_full_build((Path("foo"), Path("bar"))) == [
        Path("foo"),
        Path("bar"),
        Path(CONFIG_FILENAME),
    ]
