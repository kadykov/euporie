"""Test cases for :py:mod:`euporie.core.formatted_text.html` module."""

from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import to_plain_text

from euporie.core.formatted_text.html import HTML


def test_inline_whitespace() -> "None":
    """Whitespace between inline elements is correctly collapsed."""
    data = "a b  c \n d\ne"
    expected = "a b c d e"
    result = to_plain_text(to_formatted_text(HTML(data, width=9)))
    assert result == expected


def test_nested_list_linebreaks() -> "None":
    """There are no extra linebreaks in nested lists."""
    data = "<ol><li>a<ul><li>a</li><li>b</li></ul></li><li>b</li></ol>"
    expected = " 1. a   \n     • a\n     • b\n 2. b   "
    result = to_plain_text(HTML(data, width=8))
    assert result == expected

    data = "<ul><li>a<ol><li>a</li><li>b</li></ol></li><li>b</li></ul>"
    expected = " • a    \n    1. a\n    2. b\n • b    "
    result = to_plain_text(HTML(data, width=8))
    assert result == expected


def test_hidden() -> "None":
    """Text with ``visibility: hidden`` is rendered as spaces."""
    data = 'a <u style="visibility:hidden">b</u> c'
    expected = "a   c"
    result = HTML(data, width=5)
    assert to_plain_text(result) == expected


def test_hidden_underline_removal() -> "None":
    """Underline attribute should be removed from hidden elements."""
    data = 'a <u style="visibility:hidden">b</u> c'
    result = HTML(data, width=5).formatted_text
    assert "nounderline" in result[1][0]


def test_text_wrapping() -> "None":
    """Text wraps a word boundaries."""
    data = "aa bb cc"
    expected = "aa bb  \ncc     "
    result = to_plain_text(HTML(data, width=7))
    assert result == expected


def test_inline_element_wrapping() -> "None":
    """Text in inline elements is wrapped."""
    data = "aa <span>bb cc dd</span>"
    expected = "aa bb \ncc dd "
    result = to_plain_text(HTML(data, width=6))
    assert result == expected


def test_enclosed_paragraph_newlines() -> "None":
    """Enclosed an unenclosed paragraph margins are consistent."""
    data = "<p>a</p><p>b</b><p>c</p>"
    expected = to_plain_text(HTML(f"<div>{data}</div>", width=3))
    result = to_plain_text(HTML(f"{data}", width=3))
    assert result == expected


def test_parent_style_class_inherited() -> "None":
    """Style classes of parent elements are inherited."""
    data = "<section><div><p>pp</p></div></section>"
    result = HTML(data, width=5).formatted_text
    assert "html,section,div,p" in result[0][0]


def test_single_hr() -> "None":
    """A single <hr> has its margins stripped."""
    data = "<hr>"
    expected = "───"
    result = to_plain_text(HTML(data, width=3))
    assert result == expected


def test_nested_block_margins() -> "None":
    """Margins are stripped from blocks at the start and end of blocks."""
    data = "<hr><div><hr></div><hr>"
    expected = "─\n \n─\n \n─"
    result = to_plain_text(HTML(data, width=1))
    assert result == expected


def test_details_summary() -> "None":
    """A <summary> renders as expected."""
    data = "<details><summary>a a a</summary>b b b</details>"
    expected = " ⮟ a a \n   a   \n       \n   b b \n   b   "
    result = to_plain_text(HTML(data, width=7))
    assert result == expected


def test_multiple_css_selectors() -> "None":
    """Comma separated CSS selectors are interpreted."""
    data = '<style>.a,.b{color:red}</style><i class="a">a</i><i class="b">b</i>'
    expected = [("class:html,i  fg:#ff0000", "a"), ("class:html,i  fg:#ff0000", "b")]
    result = to_formatted_text(HTML(data, width=2))
    print(result.__repr__())
    assert result == expected
