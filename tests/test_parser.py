"""Tests for the Markdown and HTML parse modes.

Both parsers return `{"message": str, "entities": list | None}`, where
`entities` is None (not []) when nothing was formatted, and the Markdown parser
works by rewriting its delimiters into HTML and delegating to the HTML parser.
"""

import pytest

from newbiegram import raw
from newbiegram.parser import html, markdown


@pytest.fixture
def md():
    return markdown.Markdown(None)


@pytest.fixture
def hp():
    return html.HTML(None)


def _types(entities):
    return {entity.QUALNAME for entity in entities or []}


async def test_plain_text_has_no_entities(md):
    result = await md.parse("hello world")

    assert result["message"] == "hello world"
    assert result["entities"] is None


async def test_bold_delimiter(md):
    """NewbieGram uses ** for bold, keeping __ free for italic."""
    result = await md.parse("**bold**")

    assert result["message"] == "bold"
    assert _types(result["entities"]) == {"types.MessageEntityBold"}


async def test_italic_delimiter(md):
    result = await md.parse("__italic__")

    assert result["message"] == "italic"
    assert _types(result["entities"]) == {"types.MessageEntityItalic"}


async def test_underline_delimiter(md):
    """Underline uses --text--."""
    result = await md.parse("--underline--")

    assert result["message"] == "underline"
    assert _types(result["entities"]) == {"types.MessageEntityUnderline"}


async def test_strikethrough(md):
    result = await md.parse("~~strike~~")

    assert result["message"] == "strike"
    assert _types(result["entities"]) == {"types.MessageEntityStrike"}


async def test_code_is_preserved_verbatim(md):
    """Contents of a code span must not be re-parsed as other delimiters."""
    result = await md.parse("`**not bold**`")

    assert result["message"] == "**not bold**"
    assert _types(result["entities"]) == {"types.MessageEntityCode"}


async def test_pre_code_block(md):
    result = await md.parse("```\nplain\n```")

    assert "plain" in result["message"]
    assert "types.MessageEntityPre" in _types(result["entities"])


async def test_nested_formatting(md):
    result = await md.parse("**bold __and italic__**")

    assert "bold" in result["message"]
    assert "and italic" in result["message"]
    assert {"types.MessageEntityBold", "types.MessageEntityItalic"} <= _types(result["entities"])


async def test_entities_are_sorted_by_offset(md):
    """Telegram requires entities in offset order."""
    result = await md.parse("**a** and __b__ and ~~c~~")

    offsets = [entity.offset for entity in result["entities"]]
    assert offsets == sorted(offsets)


async def test_zero_length_entities_are_dropped(hp):
    result = await hp.parse("a<b></b>")

    assert all(entity.length > 0 for entity in result["entities"] or [])


async def test_html_escape_and_entities(hp):
    result = await hp.parse("<b>bold</b>")

    assert result["message"] == "bold"
    assert _types(result["entities"]) == {"types.MessageEntityBold"}


async def test_html_unescapes_characters(hp):
    result = await hp.parse("&lt;tag&gt; &amp; more")

    assert result["message"] == "<tag> & more"


async def test_html_strips_unsupported_tags(hp):
    result = await hp.parse("hello <i>world</i>")

    assert "world" in result["message"]
    assert "<i>" not in result["message"]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<b>x</b>", "MessageEntityBold"),
        ("<i>x</i>", "MessageEntityItalic"),
        ("<u>x</u>", "MessageEntityUnderline"),
        ("<s>x</s>", "MessageEntityStrike"),
        ("<code>x</code>", "MessageEntityCode"),
        ("<spoiler>x</spoiler>", "MessageEntitySpoiler"),
    ],
)
async def test_html_tag_mapping(hp, source, expected):
    result = await hp.parse(source)

    assert f"types.{expected}" in _types(result["entities"])


async def test_html_link(hp):
    result = await hp.parse('<a href="https://example.com">link</a>')

    assert result["message"] == "link"
    entity = next(e for e in result["entities"] if e.QUALNAME == "types.MessageEntityTextUrl")
    assert entity.url == "https://example.com"


def test_unparse_roundtrip_markdown():
    """unparse must invert parse, so editing a message does not lose formatting."""
    entities = [
        raw.types.MessageEntityBold(offset=0, length=4),
        raw.types.MessageEntityItalic(offset=9, length=6),
    ]

    assert markdown.Markdown.unparse("bold and italic", entities) == "**bold** and __italic__"


def test_unparse_roundtrip_html():
    entities = [
        raw.types.MessageEntityBold(offset=0, length=4),
        raw.types.MessageEntityCode(offset=9, length=1),
    ]

    assert html.HTML.unparse("bold and x", entities) == "<b>bold</b> and <code>x</code>"
