# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

from pathlib import Path

import pytest

from antsibull_nox.releaser._yaml import YAMLEditor

TEST_YAML_EDITOR_DATA: list[tuple[str, str, str | None, str, str]] = [
    (
        """\
foo: bar
""",
        "foo",
        "bar",
        "baz",
        """\
foo: baz
""",
    ),
    (
        """\
foo: x
""",
        "foo",
        "x",
        "y",
        """\
foo: y
""",
    ),
    (
        """\
foo: "bar"
""",
        "foo",
        "bar",
        "baz",
        """\
foo: "baz"
""",
    ),
    (
        """\
foo:   'bar'
""",
        "foo",
        "bar",
        "baz",
        """\
foo:   'baz'
""",
    ),
    (
        """\
---
foo: bar
...
""",
        "foo",
        "bar",
        "baz",
        """\
---
foo: baz
...
""",
    ),
    (
        """\
---
# foo: bar
foo: bar
""",
        "foo",
        "bar",
        "baz",
        """\
---
# foo: bar
foo: baz
""",
    ),
    (
        """\
...
# foo: bar
foo: bar
""",
        "foo",
        None,
        "baz",
        """\
foo: baz
...
# foo: bar
foo: bar
""",
    ),
    (
        """\
# Foo bar
---
...
foo: bar
""",
        "foo",
        None,
        "bar",
        """\
# Foo bar
---
foo: bar
...
foo: bar
""",
    ),
    (
        """\
mee: mah
---
foo: baz
""",
        "foo",
        None,
        "bar",
        """\
mee: mah
foo: bar
---
foo: baz
""",
    ),
    (
        "foo: bar\r\nbaz: bam\n\r",
        "foo",
        "bar",
        "boom",
        "foo: boom\nbaz: bam\n\n",
    ),
]


@pytest.mark.parametrize(
    "input, key, expected_value, new_value, expected_output",
    TEST_YAML_EDITOR_DATA,
)
def test_YAMLEditor(
    input: str,
    key: str,
    expected_value: str | None,
    new_value: str,
    expected_output: str,
    tmp_path: Path,
) -> None:
    file = tmp_path / "test.yaml"
    file.write_bytes(input.encode("utf-8"))
    editor = YAMLEditor(path=file)
    field = editor.find(key=key)
    if expected_value is None:
        assert field == None
        field = editor.create(key=key, value=new_value)
    else:
        assert field is not None
        assert field.value == expected_value
        field.set(new_value)
    editor.write()
    with file.open("rb") as f:
        output = f.read().decode("utf-8")
    assert output == expected_output


TEST_YAML_FAIL_DATA: list[tuple[str, str, str]] = [
    (
        """\
foo:
  bar: baz
""",
        "foo",
        "^Can only work on simple string-valued YAML keys 'foo'$",
    ),
    (
        """\
foo: >-
  bar
""",
        "foo",
        "^Can only work on simple string-valued YAML keys 'foo'$",
    ),
    (
        """\
foo: [bar]
""",
        "foo",
        "^Can only work on simple string-valued YAML keys 'foo'$",
    ),
]


@pytest.mark.parametrize(
    "input, key, expected_error",
    TEST_YAML_FAIL_DATA,
)
def test_YAMLEditor_fail(
    input: str,
    key: str,
    expected_error: str,
    tmp_path: Path,
) -> None:
    file = tmp_path / "test.yaml"
    file.write_text(input, encoding="utf-8")
    editor = YAMLEditor(path=file)
    with pytest.raises(match=expected_error):
        editor.find(key=key)
