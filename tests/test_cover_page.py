"""Tests for the cover-page rendering in the HTML template."""

from __future__ import annotations

from epy_mdr.renderer import render_markdown
from epy_mdr.template import is_truthy


def test_cover_page_with_logo():
    src = (
        "---\n"
        "title: My Report\n"
        "subtitle: A study\n"
        "author: ANM\n"
        "cover: true\n"
        "logo: figures/logo.png\n"
        "---\n\n"
        "Body text.\n"
    )
    html = render_markdown(src)
    assert '<section class="cover-page">' in html
    assert 'class="cover-logo"' in html
    assert 'src="figures/logo.png"' in html
    assert "A study" in html
    # Cover page is followed by a page break.
    assert '<div class="page-break"></div>' in html


def test_no_cover_keeps_doc_meta():
    src = "---\ntitle: Plain\nauthor: ANM\n---\n\nBody.\n"
    html = render_markdown(src)
    assert '<section class="cover-page">' not in html
    assert 'class="doc-meta"' in html


def test_cover_false_is_falsy():
    src = "---\ntitle: Plain\ncover: false\n---\n\nBody.\n"
    html = render_markdown(src)
    assert '<section class="cover-page">' not in html


def test_is_truthy_values():
    for value in ("true", "Yes", "1", "ON", " true "):
        assert is_truthy(value)
    for value in ("false", "no", "0", "", None):
        assert not is_truthy(value)
