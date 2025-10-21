# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from antsibull_nox.python.python_dependencies import (
    get_python_dependency_info,
)

from ..utils import chdir


def test_get_python_dependency_info(tmp_path: Path) -> None:
    galaxy_yml = tmp_path / "galaxy.yml"
    galaxy_yml.write_text(
        r"""
namespace: foo
name: bar
"""
    )

    plugins = tmp_path / "plugins"
    plugins.mkdir()
    module_utils = plugins / "module_utils"
    module_utils.mkdir()
    modules = plugins / "modules"
    modules.mkdir()

    module_utils_foo = module_utils / "foo.py"
    module_utils_foo.write_text(
        r"""
"""
    )

    module_utils_bar = module_utils / "bar"
    module_utils_bar.mkdir()

    module_utils_bar_init = module_utils_bar / "__init__.py"
    module_utils_bar_init.write_text(
        r"""
"""
    )

    module_utils_bar_foobarbaz = module_utils_bar / "foobarbaz.py"
    module_utils_bar_foobarbaz.write_text(
        r"""
"""
    )

    module_utils_foo = module_utils / "foo.py"
    module_utils_foo.write_text(
        r"""
"""
    )

    module_1 = modules / "module_1.py"
    module_1.write_text(
        r"""
from ansible.module_utils.basic import AnsibleModule
from ..module_utils import foo
from ansible_collections.foo.bar.plugins.module_utils.bar import run_bar, foobarbaz
from ansible_collections.foo.bar.plugins.module_utils.baz import run_baz
from ansible_collections.foo.bam.plugins.module_utils.bazbam import run_bazbam
"""
    )

    with chdir(tmp_path):
        with patch(
            "antsibull_nox.python.python_dependencies.list_all_files",
            return_value=[
                galaxy_yml,
                module_utils_foo,
                module_utils_bar_init,
                module_utils_bar_foobarbaz,
                module_1,
            ],
        ):
            get_python_dependency_info.cache_clear()
            result = get_python_dependency_info()

    assert result.file_to_module_path == {
        module_utils_foo: (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "module_utils",
            "foo",
        ),
        module_utils_bar_init: (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "module_utils",
            "bar",
        ),
        module_utils_bar_foobarbaz: (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "module_utils",
            "bar",
            "foobarbaz",
        ),
        module_1: (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "modules",
            "module_1",
        ),
    }
    assert result.module_path_to_file == {
        (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "module_utils",
            "foo",
        ): module_utils_foo,
        (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "module_utils",
            "bar",
        ): module_utils_bar_init,
        (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "module_utils",
            "bar",
            "foobarbaz",
        ): module_utils_bar_foobarbaz,
        (
            "ansible_collections",
            "foo",
            "bar",
            "plugins",
            "modules",
            "module_1",
        ): module_1,
    }
    assert result.file_to_imported_modules == {
        module_utils_foo: (frozenset(), frozenset()),
        module_utils_bar_init: (frozenset(), frozenset()),
        module_utils_bar_foobarbaz: (frozenset(), frozenset()),
        module_1: (
            frozenset(
                [
                    (
                        "ansible_collections",
                        "foo",
                        "bar",
                        "plugins",
                        "module_utils",
                        "foo",
                    ),
                    (
                        "ansible_collections",
                        "foo",
                        "bar",
                        "plugins",
                        "module_utils",
                        "bar",
                    ),
                    (
                        "ansible_collections",
                        "foo",
                        "bar",
                        "plugins",
                        "module_utils",
                        "bar",
                        "foobarbaz",
                    ),
                ]
            ),
            frozenset(
                [module_utils_foo, module_utils_bar_init, module_utils_bar_foobarbaz]
            ),
        ),
    }
    assert result.file_to_imported_by_modules == {
        module_utils_foo: (
            frozenset(
                [
                    (
                        "ansible_collections",
                        "foo",
                        "bar",
                        "plugins",
                        "modules",
                        "module_1",
                    )
                ]
            ),
            frozenset([module_1]),
        ),
        module_utils_bar_init: (
            frozenset(
                [
                    (
                        "ansible_collections",
                        "foo",
                        "bar",
                        "plugins",
                        "modules",
                        "module_1",
                    )
                ]
            ),
            frozenset([module_1]),
        ),
        module_utils_bar_foobarbaz: (
            frozenset(
                [
                    (
                        "ansible_collections",
                        "foo",
                        "bar",
                        "plugins",
                        "modules",
                        "module_1",
                    )
                ]
            ),
            frozenset([module_1]),
        ),
        module_1: (
            frozenset([]),
            frozenset([]),
        ),
    }
