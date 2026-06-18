"""Tests for the cover-page rendering and HTML template helpers."""

from __future__ import annotations

from epy_mdr.renderer import render_markdown
from epy_mdr.template import (
    _cover_page_block,
    _front_matter_block,
    _load_base_css,
    _load_mathjax_script,
    is_truthy,
)


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


# ---------------------------------------------------------------------------
# XSS escaping — metadata values must not allow raw HTML injection.
# ---------------------------------------------------------------------------

_XSS_PAYLOAD = '<script>alert("xss")</script>'
_XSS_ESCAPED = "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
# html.escape encodes ' as &#x27; and " as &quot; in element content.
_XSS_ESCAPED_QUOTE = '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'


def test_front_matter_block_escapes_title():
    out = _front_matter_block({"title": _XSS_PAYLOAD})
    assert _XSS_PAYLOAD not in out
    assert "<script>" not in out


def test_front_matter_block_escapes_author():
    out = _front_matter_block({"author": _XSS_PAYLOAD})
    assert _XSS_PAYLOAD not in out
    assert "<script>" not in out


def test_front_matter_block_escapes_date():
    out = _front_matter_block({"date": _XSS_PAYLOAD})
    assert _XSS_PAYLOAD not in out
    assert "<script>" not in out


def test_cover_page_block_escapes_title():
    out = _cover_page_block({"title": _XSS_PAYLOAD})
    assert _XSS_PAYLOAD not in out
    assert "<script>" not in out


def test_cover_page_block_escapes_subtitle():
    out = _cover_page_block({"subtitle": _XSS_PAYLOAD})
    assert _XSS_PAYLOAD not in out
    assert "<script>" not in out


def test_cover_page_block_escapes_author():
    out = _cover_page_block({"author": _XSS_PAYLOAD})
    assert _XSS_PAYLOAD not in out
    assert "<script>" not in out


def test_cover_page_block_escapes_date():
    out = _cover_page_block({"date": _XSS_PAYLOAD})
    assert _XSS_PAYLOAD not in out
    assert "<script>" not in out


def test_cover_page_block_escapes_logo_src():
    """Logo src attribute — injected double-quote must be encoded.

    The ``"`` in the logo path is escaped to ``&quot;`` so it cannot
    break out of the attribute value and inject new attributes.
    """
    malicious_logo = '" onerror="alert(1)"'
    out = _cover_page_block({"logo": malicious_logo})
    # The raw (unescaped) payload must not appear verbatim.
    assert malicious_logo not in out
    # The ``"`` that would break the attribute must be encoded.
    assert "&quot;" in out or "&#x22;" in out


def test_render_markdown_escapes_xss_in_front_matter():
    """End-to-end: XSS in YAML front matter must be escaped in output."""
    src = (
        "---\n"
        f'title: {_XSS_PAYLOAD}\n'
        f'author: {_XSS_PAYLOAD}\n'
        "---\n\n"
        "Body.\n"
    )
    out = render_markdown(src)
    assert "<script>alert" not in out


# ---------------------------------------------------------------------------
# Asset caching — repeated calls must return the same object (lru_cache).
# ---------------------------------------------------------------------------

def test_load_base_css_is_cached():
    """_load_base_css returns the same str object on repeated calls."""
    first = _load_base_css()
    second = _load_base_css()
    assert first is second
    assert len(first) > 0


def test_load_mathjax_script_is_cached():
    """_load_mathjax_script returns the same str object on repeated calls."""
    first = _load_mathjax_script()
    second = _load_mathjax_script()
    assert first is second
    assert "<script>" in first
