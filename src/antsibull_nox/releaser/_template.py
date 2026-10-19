# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Templating helpers.
"""

from __future__ import annotations

import re
import typing as t

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping


_PLACEHOLDER = re.compile("\\{([^{}\\\\\n]+)\\}")

_ESCAPE_SEQUENCES = {
    "\\": "\\",
    "{": "{",
    "}": "}",
    "n": "\n",
    "t": "\t",
}


def template_string(template: str, *, variables: Mapping[str, str]) -> str:
    """
    Given a string, template it.
    """
    result = []
    index = 0
    length = len(template)
    escape_idx = template.find("\\", index)
    placeholder = _PLACEHOLDER.search(template, pos=index)

    def handle_escape(index: int, escape_idx: int) -> tuple[int, int]:
        if escape_idx > index:
            result.append(template[index:escape_idx])
        index = escape_idx + 2
        if index > length:
            raise ValueError(f"Template {template!r} ends with single backslash.")
        replacement = _ESCAPE_SEQUENCES.get(template[escape_idx + 1])
        if replacement is None:
            raise ValueError(
                f"Invalid escape sequence {template[escape_idx:escape_idx + 2]}"
                f" in template {template!r}."
            )
        result.append(replacement)
        escape_idx = template.find("\\", index)
        return index, escape_idx

    while index < length:
        if placeholder is None:
            if escape_idx < 0:
                result.append(template[index:])
                break
            index, escape_idx = handle_escape(index, escape_idx)
            continue
        placeholder_idx = placeholder.start()
        if 0 <= escape_idx < placeholder_idx:
            index, escape_idx = handle_escape(index, escape_idx)
            continue
        if placeholder_idx > index:
            result.append(template[index:placeholder_idx])
        variable = placeholder.group(1).strip()
        replacement = variables.get(variable)
        if replacement is None:
            known_vars = ", ".join([f"{v!r}" for v in sorted(variables)])
            raise ValueError(
                f"Unknown variable {variable!r} in template {template!r}."
                f" Known variables are: {known_vars}"
            )
        result.append(replacement)
        index = placeholder.end()
        placeholder = _PLACEHOLDER.search(template, pos=index)
    return "".join(result)


__all__ = ("template_string",)
