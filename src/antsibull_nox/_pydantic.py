# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2024

# ========================================================================
# **Vendored** from antsibull-core.
#
# I vendored this to avoid depending on antsibull-core only for this.
# TBH, most of this should be part of pydantic anyway. See
# https://github.com/pydantic/pydantic/discussions/2652 for a discussion
# on this.
#
# pylint: disable=missing-function-docstring
# ========================================================================

"""
Helpers for pydantic.
"""

from __future__ import annotations

import typing as t
from collections.abc import Callable, Collection

import pydantic as p

if t.TYPE_CHECKING:
    from typing_extensions import TypeGuard


def _is_basemodel(a_type: t.Any) -> TypeGuard[type[p.BaseModel]]:
    try:
        return issubclass(a_type, p.BaseModel)
    except TypeError:
        # If inspect.isclass(a_type) is checked first, no TypeError happens for
        # Python 3.11+.

        # On Python 3.9 and 3.10, issubclass(dict[int, int], p.BaseModel) raises
        # "TypeError: issubclass() arg 1 must be a class".
        # (https://github.com/pydantic/pydantic/discussions/5970)
        return False


def _modify_config(
    cls: type[p.BaseModel],
    processed_classes: set[type[p.BaseModel]],
    change_config: Callable[[p.ConfigDict], bool],
) -> bool:
    if cls in processed_classes:
        return False
    change = False
    for field_info in cls.model_fields.values():
        if _is_basemodel(field_info.annotation):
            change |= _modify_config(
                field_info.annotation,
                processed_classes,
                change_config,
            )
        for subcls in t.get_args(field_info.annotation):
            if _is_basemodel(subcls):
                change |= _modify_config(subcls, processed_classes, change_config)
    change |= change_config(cls.model_config)
    if change:
        cls.model_rebuild(force=True)
    processed_classes.add(cls)
    return change


def set_extras(
    models: type[p.BaseModel] | Collection[type[p.BaseModel]],
    value: t.Literal["allow", "ignore", "forbid"],
) -> None:
    def change_config(model_config: p.ConfigDict) -> bool:
        if model_config.get("extra") == value:
            return False
        model_config["extra"] = value
        return True

    processed_classes: set[type[p.BaseModel]] = set()
    if isinstance(models, Collection):
        for cls in models:
            _modify_config(cls, processed_classes, change_config)
    else:
        _modify_config(models, processed_classes, change_config)


def forbid_extras(models: type[p.BaseModel] | Collection[type[p.BaseModel]]) -> None:
    set_extras(models, "forbid")


def get_formatted_error_messages(error: p.ValidationError) -> list[str]:
    def format_error(err) -> str:
        location = " -> ".join(str(loc) for loc in err["loc"])
        return f'{location}: {err["msg"]}'

    return [format_error(err) for err in error.errors()]
