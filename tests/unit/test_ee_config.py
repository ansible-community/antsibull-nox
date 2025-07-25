# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

from __future__ import annotations

import re
import typing as t

import pytest

from antsibull_nox.ee_config import (
    create_ee_config,
    set_value,
)


def re_match(value: str) -> str:
    return f"^{re.escape(value)}$"


SET_VALUE_DATA: list[tuple[dict[str, t.Any], list[str], t.Any, dict[str, t.Any]]] = [
    (
        {},
        ["foo"],
        "bar",
        {
            "foo": "bar",
        },
    ),
    (
        {},
        ["foo", "bam"],
        "boo",
        {
            "foo": {
                "bam": "boo",
            },
        },
    ),
    (
        {
            "foo": {
                "bar": "baz",
            },
        },
        ["foo", "bam"],
        "boo",
        {
            "foo": {
                "bar": "baz",
                "bam": "boo",
            },
        },
    ),
]


@pytest.mark.parametrize(
    "destination, path, value, expected",
    SET_VALUE_DATA,
)
def test_set_value(
    destination: dict[str, t.Any],
    path: list[str],
    value: t.Any,
    expected: dict[str, t.Any],
) -> None:
    set_value(destination, path, value)
    assert destination == expected


SET_VALUE_FAIL_DATA: list[tuple[dict[str, t.Any], list[str], t.Any, str]] = [
    (
        {
            "foo": [],
        },
        ["foo", "bar"],
        "bar",
        re_match("Expected a dictionary at foo, but found <class 'list'>"),
    ),
]


@pytest.mark.parametrize(
    "destination, path, value, expected_regex",
    SET_VALUE_FAIL_DATA,
)
def test_set_value_fail(
    destination: dict[str, t.Any],
    path: list[str],
    value: t.Any,
    expected_regex: str,
) -> None:
    with pytest.raises(ValueError, match=expected_regex):
        set_value(destination, path, value)


CREATE_EE_CONFIG_DATA: list[
    tuple[
        int,
        str | None,
        bool,
        dict[str, t.Any] | None,
        dict[str, t.Any] | None,
        dict[str, t.Any],
    ]
] = [
    (
        3,
        "foo-bar",
        False,
        None,
        None,
        {
            "images": {
                "base_image": {
                    "name": "foo-bar",
                },
            },
            "version": 3,
        },
    ),
    (
        3,
        "foo-bar",
        True,
        {
            "foo": "bar",
        },
        {
            "images": {
                "base_image": {
                    "name": "baz-bam",
                },
            },
        },
        {
            "dependencies": {
                "foo": "bar",
            },
            "images": {
                "base_image": {
                    "name": "baz-bam",
                },
            },
            "version": 3,
        },
    ),
]


@pytest.mark.parametrize(
    "version, base_image, base_image_is_default, dependencies, config, expected",
    CREATE_EE_CONFIG_DATA,
)
def test_create_ee_config(
    version: int,
    base_image: str | None,
    base_image_is_default: bool,
    dependencies: dict[str, t.Any] | None,
    config: dict[str, t.Any] | None,
    expected: dict[str, t.Any],
) -> None:
    actual = create_ee_config(
        version=version,  # type: ignore
        base_image=base_image,
        base_image_is_default=base_image_is_default,
        dependencies=dependencies,
        config=config,
    )
    assert actual == expected


CREATE_EE_CONFIG_FAIL_DATA: list[
    tuple[int, str | None, bool, dict[str, t.Any] | None, dict[str, t.Any] | None, str]
] = [
    (
        3,
        None,
        False,
        None,
        {
            "version": 3,
        },
        re_match(
            "Value version is already present in the EE config (type <class 'int'>);"
            " cannot overwrite with value (type <class 'int'>) from config"
        ),
    ),
    (
        3,
        "foo-bar",
        False,
        None,
        {
            "images": {
                "base_image": {
                    "name": "baz-bam",
                },
            },
        },
        re_match(
            "Value images.base_image.name is already present in the EE config (type <class 'str'>);"
            " cannot overwrite with value (type <class 'str'>) from config"
        ),
    ),
    (
        3,
        "foo-bar",
        False,
        None,
        {
            "images": [],
        },
        re_match(
            "Value images is already present in the EE config (type <class 'dict'>);"
            " cannot overwrite with value (type <class 'list'>) from config"
        ),
    ),
    (
        -1,
        None,
        False,
        None,
        {},
        re_match("Invalid EE definition version -1"),
    ),
]


@pytest.mark.parametrize(
    "version, base_image, base_image_is_default, dependencies, config, expected_regex",
    CREATE_EE_CONFIG_FAIL_DATA,
)
def test_create_ee_config_fail(
    version: int,
    base_image: str | None,
    base_image_is_default: bool,
    dependencies: dict[str, t.Any] | None,
    config: dict[str, t.Any] | None,
    expected_regex: str,
) -> None:
    with pytest.raises(ValueError, match=expected_regex):
        create_ee_config(
            version=version,  # type: ignore
            base_image=base_image,
            base_image_is_default=base_image_is_default,
            dependencies=dependencies,
            config=config,
        )
