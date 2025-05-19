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

from antsibull_nox.data.antsibull_nox_data_util import setup
from antsibull_nox.sessions.extra_checks import ActionGroup


def compile_patterns(
    config: list[ActionGroup], errors: list[str]
) -> dict[str, re.Pattern] | None:
    patterns: dict[str, re.Pattern] = {}
    for action_group in config:
        if action_group.name in config:
            errors.append(
                f"noxfile.py: Action group {action_group.name!r} defined multiple times"
            )
            return None
        patterns[action_group.name] = re.compile(action_group.pattern)
    return patterns


def load_redirects(
    config: list[ActionGroup], errors: list[str], meta_runtime: str
) -> dict[str, list[str]]:
    # Load redirects
    try:
        with open(meta_runtime, "rb") as f:
            data = yaml.safe_load(f)
        action_groups = data.get("action_groups", {})
    except Exception as exc:
        errors.append(f"{meta_runtime}: cannot load action groups: {exc}")
        return {}

    if not isinstance(action_groups, dict):
        errors.append(f"{meta_runtime}: action_groups is not a dictionary")
        return {}
    if not all(
        isinstance(k, str) and isinstance(v, list) for k, v in action_groups.items()
    ):
        errors.append(
            f"{meta_runtime}: action_groups is not a dictionary mapping strings to list of strings"
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
            errors.append(
                f"{meta_runtime}: found unknown action group"
                f" {action_group!r}; likely noxfile needs updating"
            )
        else:
            action_groups[action_group] = [
                element for element in elements if isinstance(element, str)
            ]
    for action_group in config:
        if action_group.name not in action_groups:
            errors.append(
                f"{meta_runtime}: cannot find action group"
                f" {action_group.name!r}; likely noxfile needs updating"
            )

    return action_groups


def load_docs(path: str, errors: list[str]) -> dict[str, t.Any] | None:
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
        errors.append(f"{path}: cannot find DOCUMENTATION end")
    if not documentation:
        errors.append(f"{path}: cannot find DOCUMENTATION")
        return None

    try:
        docs = yaml.safe_load("\n".join(documentation))
        if not isinstance(docs, dict):
            raise Exception("is not a top-level dictionary")
        return docs
    except Exception as exc:
        errors.append(f"{path}: cannot load DOCUMENTATION as YAML: {exc}")
        return None


def scan(config: list[ActionGroup], errors: list[str]) -> None:
    patterns = compile_patterns(config, errors)
    if patterns is None:
        return

    meta_runtime = "meta/runtime.yml"
    action_groups = load_redirects(config, errors, meta_runtime)

    modules_directory = "plugins/modules/"
    modules_suffix = ".py"

    for file in os.listdir(modules_directory):
        if not file.endswith(modules_suffix):
            continue
        module_name = file[: -len(modules_suffix)]

        for action_group in config:
            action_group_content = action_groups.get(action_group.name) or []
            path = os.path.join(modules_directory, file)

            if not patterns[action_group.name].match(module_name):
                if module_name in action_group_content:
                    errors.append(
                        f"{path}: module is in action group {action_group.name!r}"
                        " despite not matching its pattern as defined in noxfile"
                    )
                continue

            should_be_in_action_group = (
                module_name not in action_group.exclusions
                if action_group.exclusions
                else True
            )

            if should_be_in_action_group:
                if module_name not in action_group_content:
                    errors.append(
                        f"{meta_runtime}: module {module_name!r} is not part"
                        f" of {action_group.name!r} action group"
                    )
                else:
                    action_group_content.remove(module_name)

            docs = load_docs(path, errors)
            if docs is None:
                continue

            docs_fragments = docs.get("extends_documentation_fragment") or []
            is_in_action_group = action_group.doc_fragment in docs_fragments

            if should_be_in_action_group != is_in_action_group:
                if should_be_in_action_group:
                    errors.append(
                        f"{path}: module does not document itself as part of"
                        f" action group {action_group.name!r}, but it should;"
                        f" you need to add {action_group.doc_fragment} to"
                        f' "extends_documentation_fragment" in DOCUMENTATION'
                    )
                else:
                    errors.append(
                        f"{path}: module documents itself as part of"
                        f" action group {action_group.name!r}, but it should not be"
                    )

    for action_group in config:
        action_group_content = action_groups.get(action_group.name) or []
        for module_name in action_group_content:
            errors.append(
                f"{meta_runtime}: module {module_name} mentioned"
                f" in {action_group.name!r} action group does not exist"
                " or does not match pattern defined in noxfile"
            )


def main() -> int:
    """Main entry point."""
    paths, extra_data = setup()

    if not isinstance(extra_data.get("config"), list):
        raise ValueError("config is not a list")
    if not all(isinstance(cfg, dict) for cfg in extra_data["config"]):
        raise ValueError("config is not a list of dictionaries")
    config = [ActionGroup(**cfg) for cfg in extra_data["config"]]

    errors: list[str] = []
    scan(config, errors)

    for error in sorted(errors):
        print(error)
    return len(errors) > 0


if __name__ == "__main__":
    sys.exit(main())
