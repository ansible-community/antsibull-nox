# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

from __future__ import annotations

from pathlib import Path

import pytest

from antsibull_nox.python.imports import (
    PythonImport,
    PythonModule,
    get_all_module_data,
    get_imported_packages,
    get_module_data_from_source_root,
)

PYTHON_IMPORT_BELONGS_TO: list[tuple[PythonImport, tuple[str, ...], bool]] = [
    (PythonImport(("foo",)), ("foo", "bar"), False),
    (PythonImport(("foo",)), ("foo",), True),
    (PythonImport(("foo", "bar")), ("foo",), True),
]


@pytest.mark.parametrize(
    "python_import, module_path, expected_result",
    PYTHON_IMPORT_BELONGS_TO,
)
def test_python_import_belongs_to(
    python_import: PythonImport, module_path: tuple[str, ...], expected_result: bool
) -> None:
    assert python_import.belongs_to(module_path) == expected_result


GET_IMPORTED_PACKAGES: list[tuple[tuple[str, ...], str, set[PythonImport], bool]] = [
    (
        ("foo", "bar", "baz"),
        r"""
import baz
import baz.bam
import baz.bam.bar as fdsa
from foo.baz import bam_1
from . import bam_2 as asdf
from .bar import bam_3
from ..bar import bam_4
from ...bar import bam_5
""",
        {
            PythonImport(
                symbol_path=("baz",),
            ),
            PythonImport(
                symbol_path=(
                    "baz",
                    "bam",
                ),
            ),
            PythonImport(
                symbol_path=(
                    "baz",
                    "bam",
                    "bar",
                ),
            ),
            PythonImport(
                symbol_path=(
                    "foo",
                    "bar",
                    "bar",
                    "bam_3",
                ),
            ),
            PythonImport(
                symbol_path=(
                    "foo",
                    "bar",
                    "bam_4",
                ),
            ),
            PythonImport(
                symbol_path=(
                    "foo",
                    "bar",
                    "bam_2",
                ),
            ),
            PythonImport(
                symbol_path=(
                    "bar",
                    "bam_5",
                ),
            ),
            PythonImport(("foo", "baz", "bam_1")),
        },
        True,
    ),
    (
        ("foo", "bar", "baz"),
        r"""
from .bam import bam_1
from ..bam import bam_2
from ...bam import bam_3
from ....bam import bam_4
from .....bam import bam_5
""",
        {
            PythonImport(
                symbol_path=(
                    "foo",
                    "bar",
                    "bam",
                    "bam_1",
                ),
            ),
            PythonImport(
                symbol_path=(
                    "foo",
                    "bam",
                    "bam_2",
                ),
            ),
            PythonImport(
                symbol_path=(
                    "bam",
                    "bam_3",
                ),
            ),
        },
        False,
    ),
    (
        ("foo", "bar", "baz"),
        r"""
import .bam  # syntax error
from .bam import bam_1
""",
        set(),
        False,
    ),
]


@pytest.mark.parametrize(
    "module_path, content, expected_imports, expected_parsable",
    GET_IMPORTED_PACKAGES,
)
def test_get_imported_packages(
    module_path: tuple[str, ...],
    content: str,
    expected_imports: set[PythonImport],
    expected_parsable: bool,
    tmp_path: Path,
) -> None:
    path = tmp_path / "foo.py"
    path.write_text(content)
    imports, parsable = get_imported_packages(path, module_path)
    assert imports == expected_imports
    assert parsable == expected_parsable


def test_get_module_data_from_source_root(tmp_path: Path) -> None:
    dir_1 = tmp_path / "dir_1"
    dir_1.mkdir()
    file_1 = dir_1 / "file_1.py"
    file_1.write_text(
        r"""
import foo
from .bar import asdf
"""
    )
    assert get_module_data_from_source_root(
        file_1, source_root=tmp_path
    ) == PythonModule(
        path=file_1,
        module_path=(
            "dir_1",
            "file_1",
        ),
        imports=frozenset(
            {
                PythonImport(
                    symbol_path=(
                        "dir_1",
                        "bar",
                        "asdf",
                    ),
                ),
                PythonImport(
                    symbol_path=("foo",),
                ),
            }
        ),
        parsable=True,
    )


def test_get_all_module_data(tmp_path: Path) -> None:
    file_1 = tmp_path / "file_1.py"
    file_1.write_text(
        r"""
import foo
from .bar import asdf
"""
    )
    dir_1 = tmp_path / "dir_1"
    dir_1.mkdir()
    file_2 = dir_1 / "file_2.py"
    file_2.write_text(
        r"""
import foo
from .bar import asdf
"""
    )
    file_3 = dir_1 / "__init__.py"
    file_3.write_text(
        r"""
import foo
from .bar import asdf
"""
    )
    file_4 = dir_1 / "foo.pyx"
    file_4.write_text(
        r"""
import bam
from .bar import fdsa
"""
    )
    result = set(get_all_module_data([(tmp_path, ("baz",))]))
    assert result == {
        PythonModule(
            path=file_1,
            module_path=(
                "baz",
                "file_1",
            ),
            imports=frozenset(
                {
                    PythonImport(
                        symbol_path=(
                            "baz",
                            "bar",
                            "asdf",
                        ),
                    ),
                    PythonImport(
                        symbol_path=("foo",),
                    ),
                }
            ),
            parsable=True,
        ),
        PythonModule(
            path=file_2,
            module_path=(
                "baz",
                "dir_1",
                "file_2",
            ),
            imports=frozenset(
                {
                    PythonImport(
                        symbol_path=("foo",),
                    ),
                    PythonImport(
                        symbol_path=(
                            "baz",
                            "dir_1",
                            "bar",
                            "asdf",
                        ),
                    ),
                }
            ),
            parsable=True,
        ),
        PythonModule(
            path=file_3,
            module_path=(
                "baz",
                "dir_1",
            ),
            imports=frozenset(
                {
                    PythonImport(
                        symbol_path=(
                            "baz",
                            "bar",
                            "asdf",
                        ),
                    ),
                    PythonImport(
                        symbol_path=("foo",),
                    ),
                }
            ),
            parsable=True,
        ),
    }

    result = set(get_all_module_data([(file_1, ("baz", "bam"))]))
    assert result == {
        PythonModule(
            path=file_1,
            module_path=(
                "baz",
                "bam",
            ),
            imports=frozenset(
                {
                    PythonImport(
                        symbol_path=(
                            "baz",
                            "bar",
                            "asdf",
                        ),
                    ),
                    PythonImport(
                        symbol_path=("foo",),
                    ),
                }
            ),
            parsable=True,
        ),
    }
