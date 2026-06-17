"""Tests for the A4 page-view preview mode in the renderer/template."""

from __future__ import annotations

from epy_mdr.renderer import render_markdown

_SRC = "# Title\n\nBody paragraph.\n"


def test_paged_marks_body_and_wraps_content():
    """``paged=True`` yields a paged body and a content wrapper.

    The body also always carries a page-size class (default Letter).
    """
    html = render_markdown(_SRC, paged=True)
    assert '<body class="paged size-letter">' in html
    assert '<main class="doc-content">' in html


def test_default_is_not_paged_but_still_wrapped():
    """The default render is not paged but keeps the wrapper.

    The page-size class is always emitted, so the default body is
    ``<body class="size-letter">`` (no ``paged``).
    """
    html = render_markdown(_SRC)
    assert "paged" not in html.split("<body", 1)[1].split(">", 1)[0]
    assert '<body class="size-letter">' in html
    assert '<main class="doc-content">' in html


def test_paged_false_explicit_matches_default():
    """An explicit ``paged=False`` behaves like the default."""
    html = render_markdown(_SRC, paged=False)
    assert "paged" not in html.split("<body", 1)[1].split(">", 1)[0]
    assert '<body class="size-letter">' in html
    assert '<main class="doc-content">' in html
