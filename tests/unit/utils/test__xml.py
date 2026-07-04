# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

from __future__ import annotations

import pytest

from antsibull_nox.utils._xml import _LINE_BREAK, Node, Text, _LineBreak


def serialize(
    node: Node | Text,
    *,
    indent: str = "",
    add_indent: str = "",
    prepend: list[str | _LineBreak] | None = None,
) -> list[str | _LineBreak]:
    result = []
    if prepend:
        result.extend(prepend)
    node._serialize(result, indent, add_indent)
    return result


def test_bad_tag() -> None:
    with pytest.raises(ValueError, match="^Invalid tag 'foo bar'$"):
        Node("foo bar")
    with pytest.raises(ValueError, match="^Invalid attribute name 'foo bar'$"):
        Node("foo", attributes={"foo bar": "baz"})
    with pytest.raises(ValueError, match="^Invalid attribute name 'foo bar'$"):
        Node("foo").set("foo bar", "baz")


def test_internal_serialize() -> None:
    node = Node("foo")
    assert serialize(node) == ["<foo/>", _LINE_BREAK]
    assert serialize(node, indent="\t") == ["<foo/>", _LINE_BREAK]
    assert serialize(node, indent="\t", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        "<foo/>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", add_indent=" ", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        "<foo/>",
        _LINE_BREAK,
    ]
    node = Node("foo", attributes={"bar": "baz"})
    assert serialize(node) == ['<foo bar="baz"/>', _LINE_BREAK]
    node.set("bar", "baz")
    node.set("bam", "boo")
    node.set("foobidoo", None)
    assert node.get("bar") == "baz"
    assert node.get("does not exist") is None
    assert node.get("does not exist", 1) == 1
    assert node.get("foobidoo") is None
    assert node.get("foobidoo", 1) is None
    assert serialize(node) == ['<foo bar="baz" bam="boo" foobidoo/>', _LINE_BREAK]
    assert serialize(node, indent="\t") == [
        '<foo bar="baz" bam="boo" foobidoo/>',
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" bam="boo" foobidoo/>',
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", add_indent=" ", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" bam="boo" foobidoo/>',
        _LINE_BREAK,
    ]
    node.delete("bam")
    assert serialize(node) == ['<foo bar="baz" foobidoo/>', _LINE_BREAK]
    node.append_node("child")
    assert serialize(node) == [
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "",
        "<child/>",
        _LINE_BREAK,
        "",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t") == [
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "\t",
        "<child/>",
        _LINE_BREAK,
        "\t",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "\t",
        "<child/>",
        _LINE_BREAK,
        "\t",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", add_indent=" ", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "\t ",
        "<child/>",
        _LINE_BREAK,
        "\t",
        "</foo>",
        _LINE_BREAK,
    ]
    node.append(Text("text 2"))
    assert serialize(node) == [
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t") == [
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "\t",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "\t",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", add_indent=" ", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        _LINE_BREAK,
        "\t ",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    node.children.insert(0, Text("text 1"))
    assert serialize(node) == [
        '<foo bar="baz" foobidoo>',
        "text 1",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t") == [
        '<foo bar="baz" foobidoo>',
        "text 1",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        "text 1",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", add_indent=" ", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        "text 1",
        "<child/>",
        "text 2",
        "</foo>",
        _LINE_BREAK,
    ]
    node.children.clear()
    node.append(Text("text&\n<3\x01>"))
    assert serialize(node) == [
        '<foo bar="baz" foobidoo>',
        "text&amp;\n&lt;3&#x1;&gt;",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t") == [
        '<foo bar="baz" foobidoo>',
        "text&amp;\n&lt;3&#x1;&gt;",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        "text&amp;\n&lt;3&#x1;&gt;",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(node, indent="\t", add_indent=" ", prepend=[_LINE_BREAK]) == [
        _LINE_BREAK,
        "\t",
        '<foo bar="baz" foobidoo>',
        "text&amp;\n&lt;3&#x1;&gt;",
        "</foo>",
        _LINE_BREAK,
    ]
    assert serialize(Text("foo")) == ["foo"]
    assert serialize(Text("foo"), prepend=[_LINE_BREAK]) == ["foo"]


def test_serialize() -> None:
    simple_tree = Node("foo", attributes={"bar": "baz"})
    child = simple_tree.append_node("baz")
    child.append(Text("foo\nbar\nbaz"))
    simple_tree.append_node("bam").append_node("bar")
    assert simple_tree.serialize() == (
        '<?xml version="1.1" encoding="utf-8"?>\n'
        '<foo bar="baz"><baz>foo\nbar\nbaz</baz><bam><bar/></bam></foo>'
    )
    assert (
        simple_tree.serialize(add_header=False)
        == '<foo bar="baz"><baz>foo\nbar\nbaz</baz><bam><bar/></bam></foo>'
    )
    assert simple_tree.serialize(indent="  ") == (
        '<?xml version="1.1" encoding="utf-8"?>\n'
        '<foo bar="baz"><baz>foo\nbar\nbaz</baz><bam><bar/></bam></foo>'
    )
    assert simple_tree.serialize(pretty_print=True) == (
        '<?xml version="1.1" encoding="utf-8"?>\n'
        '<foo bar="baz">\n\t<baz>foo\nbar\nbaz</baz>\n\t<bam>\n\t\t<bar/>\n\t</bam>\n</foo>\n'
    )
    assert simple_tree.serialize(pretty_print=True, indent="  ") == (
        '<?xml version="1.1" encoding="utf-8"?>\n'
        '<foo bar="baz">\n  <baz>foo\nbar\nbaz</baz>\n  <bam>\n    <bar/>\n  </bam>\n</foo>\n'
    )
