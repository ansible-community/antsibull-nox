# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

# pylint: disable=missing-function-docstring

"""
Helpers for testing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from antsibull_nox.messages import Level, Location, Message
from antsibull_nox.messages.parse import (
    parse_antsibull_docs_errors,
    parse_bare_framework_errors,
    parse_mypy_errors,
    parse_pylint_json2_errors,
    parse_ruff_check_errors,
)

PARSE_ANTSIBULL_DOCS_ERRORS_DATA: list[tuple[str, list[Message]]] = [
    (
        r"""{"messages": []}""",
        [],
    ),
    (
        r"""
Some random text.
{
  "messages": [
    {
      "path": "docs/docsite/config.yml",
      "row": null,
      "column": null,
      "message": "changelog -> write_changelog: Input should be a valid boolean, unable to interpret input"
    },
    {
      "path": "docs/docsite/extra-docs.yml",
      "row": null,
      "column": null,
      "message": "Section #0 has no content"
    },
    {
      "path": "docs/docsite/extra-docs.yml",
      "row": null,
      "column": null,
      "message": "Toctree entry in section #0 is not a list"
    },
    {
      "path": "docs/docsite/links.yml",
      "row": null,
      "column": null,
      "message": "foo: Extra inputs are not permitted"
    },
    {
      "path": "docs/docsite/rst/filter_guide.rst",
      "row": 6,
      "column": null,
      "message": "Label \"ansible_collection.community.dns.docsite.filter_guide\" does not start with expected prefix \"ansible_collections.community.dns.docsite.\""
    },
    {
      "path": "plugins/modules/adguardhome_rewrite.py",
      "row": null,
      "column": null,
      "message": "DOCUMENTATION -> options -> state -> description[2]: O(foo): option name does not reference to an existing option of the module community.dns.adguardhome_rewrite"
    }
  ],
  "success": false
}
More random text.
""",
        [
            Message(
                file="docs/docsite/config.yml",
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=(
                    "changelog -> write_changelog: Input should be a valid"
                    " boolean, unable to interpret input"
                ),
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
            Message(
                file="docs/docsite/extra-docs.yml",
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="Section #0 has no content",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
            Message(
                file="docs/docsite/extra-docs.yml",
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="Toctree entry in section #0 is not a list",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
            Message(
                file="docs/docsite/links.yml",
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="foo: Extra inputs are not permitted",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
            Message(
                file="docs/docsite/rst/filter_guide.rst",
                position=Location(line=6, column=None),
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=(
                    'Label "ansible_collection.community.dns.docsite.filter_guide"'
                    " does not start with expected prefix"
                    ' "ansible_collections.community.dns.docsite."'
                ),
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
            Message(
                file="plugins/modules/adguardhome_rewrite.py",
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message=(
                    "DOCUMENTATION -> options -> state -> description[2]: O(foo):"
                    " option name does not reference to an existing option of the"
                    " module community.dns.adguardhome_rewrite"
                ),
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
    (
        r"""Bad output.""",
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="Cannot parse antsibull-docs lint-collection-docs output: "
                "Expecting value: line 1 column 1 (char 0)\n"
                "Bad output.",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
]


@pytest.mark.parametrize(
    "output, expected_result",
    PARSE_ANTSIBULL_DOCS_ERRORS_DATA,
)
def test_parse_antsibull_docs_errors(
    output: str, expected_result: list[Message]
) -> None:
    result = parse_antsibull_docs_errors(output=output)
    print(result)
    assert result == expected_result


PARSE_BARE_FRAMEWORK_ERRORS_DATA: list[tuple[str, list[Message]]] = [
    (
        r"""{"messages": []}""",
        [],
    ),
    (
        r"""{"messages": [{"file": "meta/runtime.yml", "start": null, "end": null, "level": "error", "id": null,"""
        r""" "message": "module 'hosttech_dns_record' is not part of 'hosttech' action group", "symbol": null,"""
        r""" "hint": null, "note": null, "url": null}]}""",
        [
            Message(
                file="meta/runtime.yml",
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="module 'hosttech_dns_record' is not part of 'hosttech' action "
                "group",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
    (
        r"""{"messages": [{"file": "plugins/inventory/hosttech_dns_records.py", "start": {"line": 16, "column": null},"""
        r""" "end": null, "level": "error", "id": null, "message": "found trailing whitespace", "symbol": null, "hint":"""
        r""" null, "note": null, "url": null}]}""",
        [
            Message(
                file="plugins/inventory/hosttech_dns_records.py",
                position=Location(
                    line=16,
                    column=None,
                ),
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="found trailing whitespace",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
    (
        r"""Bad output.""",
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="Cannot parse output: Expecting value: line 1 column 1 (char "
                "0)\n"
                "Bad output.",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
    (
        r"""{"messages": [{"file": "docs/docsite/rst/hosttech_guide.rst", "start": {"line": 113, "column": 1, "exact": false},"""
        r""""end": null, "level": "error", "id": null, "message": "error: syntax error: could not find expected ':' (syntax)","""
        r""""symbol": null, "hint": null, "note": "The code block could not be exactly located in the source file. """
        r"""The line/column numbers might be off.", "url": null}, {"file": "docs/docsite/rst/hosttech_guide.rst", "start":"""
        r""" {"line": 123, "column": 1, "exact": true}, "end": null, "level": "error", "id": null, "message": "error: syntax"""
        r""" error: could not find expected ':' (syntax)", "symbol": null, "hint": null, "note": null, "url": null}]}""",
        [
            Message(
                file="docs/docsite/rst/hosttech_guide.rst",
                position=Location(line=113, column=1, exact=False),
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="error: syntax error: could not find expected ':' (syntax)",
                symbol=None,
                hint=None,
                note="The code block could not be exactly located in the source file. The line/column numbers might be off.",
                url=None,
            ),
            Message(
                file="docs/docsite/rst/hosttech_guide.rst",
                position=Location(line=123, column=1, exact=True),
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="error: syntax error: could not find expected ':' (syntax)",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
]


@pytest.mark.parametrize(
    "output, expected_result",
    PARSE_BARE_FRAMEWORK_ERRORS_DATA,
)
def test_parse_bare_framework_errors(
    output: str, expected_result: list[Message]
) -> None:
    result = parse_bare_framework_errors(output=output)
    print(result)
    assert result == expected_result


PARSE_MYPY_ERRORS_DATA: list[tuple[str, list[Message]]] = [
    (
        r"""""",
        [],
    ),
    (
        r"""
""",
        [],
    ),
    (
        r"""{"file": "ansible_collections/community/general/plugins/cache/memcached.py", "line": 254,"""
        r""" "column": 11, "message": "Incompatible types in assignment (expression has type \"None\","""
        r""" variable has type \"str\")", "hint": null, "code": "assignment", "severity": "error"}""",
        [
            Message(
                file="plugins/cache/memcached.py",
                position=Location(line=254, column=11),
                end_position=None,
                level=Level.ERROR,
                id="assignment",
                message='Incompatible types in assignment (expression has type "None", variable has type "str")',
                symbol=None,
                hint=None,
                note=None,
                url=None,
            )
        ],
    ),
    (
        r"""Bad output.""",
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="Cannot parse mypy output: Bad output.",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
]


@pytest.mark.parametrize(
    "output, expected_result",
    PARSE_MYPY_ERRORS_DATA,
)
def test_parse_mypy_errors(output: str, expected_result: list[Message]) -> None:
    result = parse_mypy_errors(
        output=output,
        root_path=Path("/root"),
        source_path=Path("/root/ansible_collections/community/general"),
    )
    print(result)
    assert result == expected_result


PARSE_PYLINT_JSON2_ERRORS_DATA: list[tuple[str, list[Message]]] = [
    (
        r"""{"messages": []}""",
        [],
    ),
    (
        r"""
{
    "messages": [
        {
            "type": "warning",
            "symbol": "pointless-statement",
            "message": "Statement seems to have no effect",
            "messageId": "W0104",
            "confidence": "UNDEFINED",
            "module": "ansible_collections.community.dns.plugins.module_utils.ips",
            "obj": "",
            "line": 43,
            "column": 0,
            "endLine": 43,
            "endColumn": 4,
            "path": "ansible_collections/community/dns/plugins/module_utils/ips.py",
            "absolutePath": "/root/ansible_collections/community/dns/plugins/module_utils/ips.py"
        }
    ],
    "statistics": {
        "messageTypeCount": {
            "fatal": 0,
            "error": 0,
            "warning": 1,
            "refactor": 0,
            "convention": 0,
            "info": 0
        },
        "modulesLinted": 92,
        "score": 9.998451772720236
    }
}
""",
        [
            Message(
                file="plugins/module_utils/ips.py",
                position=Location(
                    line=43,
                    column=0,
                ),
                end_position=None,
                level=Level.ERROR,
                id="W0104",
                message="Statement seems to have no effect",
                symbol="pointless-statement",
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
    (
        r"""Bad output.""",
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="Cannot parse pylint output: Expecting value: line 1 column 1 "
                "(char 0)\n"
                "Bad output.",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
]


@pytest.mark.parametrize(
    "output, expected_result",
    PARSE_PYLINT_JSON2_ERRORS_DATA,
)
def test_parse_pylint_json2_errors(output: str, expected_result: list[Message]) -> None:
    result = parse_pylint_json2_errors(
        output=output, source_path=Path("/root/ansible_collections/community/dns")
    )
    print(result)
    assert result == expected_result


PARSE_RUFF_CHECK_ERRORS_DATA: list[tuple[str, list[Message]]] = [
    (
        r"""[]""",
        [],
    ),
    (
        r"""[
  {
    "cell": null,
    "code": "SIM222",
    "end_location": {
      "column": 28,
      "row": 245
    },
    "filename": "/ansible_collections/community/general/plugins/cache/memcached.py",
    "fix": {
      "applicability": "unsafe",
      "edits": [
        {
          "content": "True",
          "end_location": {
            "column": 28,
            "row": 245
          },
          "location": {
            "column": 16,
            "row": 245
          }
        }
      ],
      "message": "Replace with `True`"
    },
    "location": {
      "column": 16,
      "row": 245
    },
    "message": "Use `True` instead of `True or ...`",
    "noqa_row": 245,
    "url": "https://docs.astral.sh/ruff/rules/expr-or-true"
  },
  {
    "cell": null,
    "code": "SIM103",
    "end_location": {
      "column": 25,
      "row": 251
    },
    "filename": "/ansible_collections/community/general/plugins/cache/memcached.py",
    "fix": {
      "applicability": "unsafe",
      "edits": [
        {
          "content": "return bool(foo)",
          "end_location": {
            "column": 25,
            "row": 251
          },
          "location": {
            "column": 9,
            "row": 248
          }
        }
      ],
      "message": "Replace with `return bool(foo)`"
    },
    "location": {
      "column": 9,
      "row": 248
    },
    "message": "Return the condition `bool(foo)` directly",
    "noqa_row": 248,
    "url": "https://docs.astral.sh/ruff/rules/needless-bool"
  }
]
""",
        [
            Message(
                file="plugins/cache/memcached.py",
                position=Location(line=245, column=16),
                end_position=Location(line=245, column=28),
                level=Level.ERROR,
                id="SIM222",
                message="Use `True` instead of `True or ...`",
                symbol=None,
                hint="Replace with `True`",
                note=None,
                url="https://docs.astral.sh/ruff/rules/expr-or-true",
            ),
            Message(
                file="plugins/cache/memcached.py",
                position=Location(line=248, column=9),
                end_position=Location(line=251, column=25),
                level=Level.ERROR,
                id="SIM103",
                message="Return the condition `bool(foo)` directly",
                symbol=None,
                hint="Replace with `return bool(foo)`",
                note=None,
                url="https://docs.astral.sh/ruff/rules/needless-bool",
            ),
        ],
    ),
    (
        r"""
[
  {
    "cell": null,
    "code": "invalid-syntax",
    "end_location": {
      "column": 1,
      "row": 243
    },
    "filename": "/ansible_collections/community/general/plugins/cache/memcached.py",
    "fix": null,
    "location": {
      "column": 33,
      "row": 242
    },
    "message": "Expected `:`, found newline",
    "noqa_row": null,
    "url": null
  }
]
""",
        [
            Message(
                file="plugins/cache/memcached.py",
                position=Location(
                    line=242,
                    column=33,
                ),
                end_position=Location(
                    line=243,
                    column=1,
                ),
                level=Level.ERROR,
                id="invalid-syntax",
                message="Expected `:`, found newline",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
    (
        r"""Bad output.""",
        [
            Message(
                file=None,
                position=None,
                end_position=None,
                level=Level.ERROR,
                id=None,
                message="Cannot parse ruff check output: Expecting value: line 1 "
                "column 1 (char 0)\n"
                "Bad output.",
                symbol=None,
                hint=None,
                note=None,
                url=None,
            ),
        ],
    ),
]


@pytest.mark.parametrize(
    "output, expected_result",
    PARSE_RUFF_CHECK_ERRORS_DATA,
)
def test_parse_ruff_check_errors(output: str, expected_result: list[Message]) -> None:
    result = parse_ruff_check_errors(
        output=output, source_path=Path("/ansible_collections/community/general")
    )
    print(result)
    assert result == expected_result
