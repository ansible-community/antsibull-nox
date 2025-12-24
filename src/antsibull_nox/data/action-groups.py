#!/usr/bin/env python

# Copyright (c) 2024, Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make sure all modules that should show up in the action group."""

from __future__ import annotations

import os
import re
import sys
import typing as t

import yaml

from antsibull_nox.data.antsibull_nox_data_util import (
    Message,
    report_result,
    setup,
)
from antsibull_nox.sessions.extra_checks import ActionGroup


def compile_patterns(
    config: list[ActionGroup], messages: list[Message]
) -> dict[str, re.Pattern] | None:
    patterns: dict[str, re.Pattern] = {}
    for action_group in config:
        if action_group.name in config:
            messages.append(
                Message(
                    file="noxfile.py",
                    start=None,
                    end=None,
                    level="error",
                    id=None,
                    message="Action group {action_group.name!r} defined multiple times",
                )
            )
            return None
        patterns[action_group.name] = re.compile(action_group.pattern)
    return patterns


def load_redirects(
    config: list[ActionGroup], messages: list[Message], meta_runtime: str
) -> dict[str, list[str]]:
    # Load redirects
    try:
        with open(meta_runtime, "rb") as f:
            data = yaml.safe_load(f)
        action_groups = data.get("action_groups", {})
    except Exception as exc:
        messages.append(
            Message(
                file=meta_runtime,
                start=None,
                end=None,
                level="error",
                id=None,
                message=f"cannot load action groups: {exc}",
            )
        )
        return {}

    if not isinstance(action_groups, dict):
        messages.append(
            Message(
                file=meta_runtime,
                start=None,
                end=None,
                level="error",
                id=None,
                message="action_groups is not a dictionary",
            )
        )
        return {}
    if not all(
        isinstance(k, str) and isinstance(v, list) for k, v in action_groups.items()
    ):
        messages.append(
            Message(
                file=meta_runtime,
                start=None,
                end=None,
                level="error",
                id=None,
                message="action_groups is not a dictionary mapping strings to list of strings",
            )
        )
        return {}

    # Compare meta/runtime.yml content with config
    config_groups = {cfg.name for cfg in config}
    for action_group, elements in action_groups.items():
        if action_group not in config_groups:
            if len(elements) == 1 and isinstance(elements[0], dict):
                # Special case: if an action group is there with a single metadata entry,
                # we don't complain that it shouldn't be there.
                continue
            messages.append(
                Message(
                    file=meta_runtime,
                    start=None,
                    end=None,
                    level="error",
                    id=None,
                    message=f"found unknown action group {action_group!r};"
                    " likely antsibull-nox.toml needs updating",
                )
            )
        else:
            action_groups[action_group] = [
                element for element in elements if isinstance(element, str)
            ]
    for action_group in config:
        if action_group.name not in action_groups:
            messages.append(
                Message(
                    file=meta_runtime,
                    start=None,
                    end=None,
                    level="error",
                    id=None,
                    message=f"cannot find action group {action_group.name!r};"
                    " likely antsibull-nox.toml needs updating",
                )
            )

    return action_groups


def load_docs(path: str, messages: list[Message]) -> dict[str, t.Any] | None:
    documentation = []
    in_docs = False
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("DOCUMENTATION ="):
                in_docs = True
            elif line.startswith(("'''", '"""')) and in_docs:
                in_docs = False
            elif in_docs:
                documentation.append(line)
    if in_docs:
        messages.append(
            Message(
                file=path,
                start=None,
                end=None,
                level="error",
                id=None,
                message="cannot find DOCUMENTATION end",
            )
        )
    if not documentation:
        messages.append(
            Message(
                file=path,
                start=None,
                end=None,
                level="error",
                id=None,
                message="cannot find DOCUMENTATION",
            )
        )
        return None

    try:
        docs = yaml.safe_load("\n".join(documentation))
        if not isinstance(docs, dict):
            raise Exception("is not a top-level dictionary")
        return docs
    except Exception as exc:
        messages.append(
            Message(
                file=path,
                start=None,
                end=None,
                level="error",
                id=None,
                message=f"cannot load DOCUMENTATION as YAML: {exc}",
            )
        )
        return None


def scan(config: list[ActionGroup], messages: list[Message]) -> None:
    patterns = compile_patterns(config, messages)
    if patterns is None:
        return

    meta_runtime = "meta/runtime.yml"
    action_groups = load_redirects(config, messages, meta_runtime)

    modules_directory = "plugins/modules/"
    modules_suffix = ".py"

    for file in (
        os.listdir(modules_directory) if os.path.isdir(modules_directory) else []
    ):
        if not file.endswith(modules_suffix):
            continue
        module_name = file[: -len(modules_suffix)]

        for action_group in config:
            action_group_content = action_groups.get(action_group.name) or []
            path = os.path.join(modules_directory, file)

            if not patterns[action_group.name].match(module_name):
                if module_name in action_group_content:
                    messages.append(
                        Message(
                            file=path,
                            start=None,
                            end=None,
                            level="error",
                            id=None,
                            message=f"module is in action group {action_group.name!r}"
                            " despite not matching its pattern as defined in noxfile",
                        )
                    )
                continue

            should_be_in_action_group = (
                module_name not in action_group.exclusions
                if action_group.exclusions
                else True
            )

            if should_be_in_action_group:
                if module_name not in action_group_content:
                    messages.append(
                        Message(
                            file=meta_runtime,
                            start=None,
                            end=None,
                            level="error",
                            id=None,
                            message=f"module {module_name!r} is not part"
                            f" of {action_group.name!r} action group",
                        )
                    )
                else:
                    action_group_content.remove(module_name)

            docs = load_docs(path, messages)
            if docs is None:
                continue

            docs_fragments = docs.get("extends_documentation_fragment") or []
            is_in_action_group = action_group.doc_fragment in docs_fragments

            if should_be_in_action_group != is_in_action_group:
                if should_be_in_action_group:
                    messages.append(
                        Message(
                            file=path,
                            start=None,
                            end=None,
                            level="error",
                            id=None,
                            message="module does not document itself as part of"
                            f" action group {action_group.name!r}, but it should;"
                            f" you need to add {action_group.doc_fragment} to"
                            f' "extends_documentation_fragment" in DOCUMENTATION',
                        )
                    )
                else:
                    messages.append(
                        Message(
                            file=path,
                            start=None,
                            end=None,
                            level="error",
                            id=None,
                            message="module documents itself as part of"
                            f" action group {action_group.name!r}, but it should not be",
                        )
                    )

    for action_group in config:
        action_group_content = action_groups.get(action_group.name) or []
        for module_name in action_group_content:
            messages.append(
                Message(
                    file=meta_runtime,
                    start=None,
                    end=None,
                    level="error",
                    id=None,
                    message=f"module {module_name} mentioned"
                    f" in {action_group.name!r} action group does not exist"
                    " or does not match pattern defined in noxfile",
                )
            )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()

    if not isinstance(extra_data.get("config"), list):
        raise ValueError("config is not a list")
    if not all(isinstance(cfg, dict) for cfg in extra_data["config"]):
        raise ValueError("config is not a list of dictionaries")
    config = [ActionGroup(**cfg) for cfg in extra_data["config"]]

    messages: list[Message] = []
    scan(config, messages)

    return report_result(messages)


if __name__ == "__main__":
    sys.exit(main())
