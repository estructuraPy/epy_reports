"""Tests for the adjustable page margin (front matter -> CSS + @page)."""

from __future__ import annotations

from epy_reports._core.renderer import render_markdown
from epy_reports._core.template import DEFAULT_PAGE_MARGIN, read_page_margin

_SRC = "# Title\n\nBody paragraph.\n"


def test_read_page_margin_default():
    assert read_page_margin({}) == DEFAULT_PAGE_MARGIN
    assert read_page_margin({"margin": ""}) == DEFAULT_PAGE_MARGIN


def test_read_page_margin_units_and_bare_number():
    assert read_page_margin({"margin": "40mm"}) == "40mm"
    assert read_page_margin({"margin": "1in"}) == "1in"
    assert read_page_margin({"margin": "2.5cm"}) == "2.5cm"
    assert read_page_margin({"margin": "30"}) == "30mm"


def test_read_page_margin_rejects_junk():
    # Anything that is not a plain CSS length falls back to the default,
    # so the value is always safe to inline without escaping.
    assert read_page_margin({"margin": "huge"}) == DEFAULT_PAGE_MARGIN
    assert (
        read_page_margin({"margin": "10mm; color:red"})
        == DEFAULT_PAGE_MARGIN
    )


def test_preview_emits_page_margin_var():
    html = render_markdown(_SRC, paged=True, page_size="letter")
    assert "--page-margin: 25mm;" in html


def test_custom_margin_flows_to_preview_var():
    src = "---\nmargin: 40mm\n---\n\n# Title\n\nBody.\n"
    html = render_markdown(src, paged=True)
    assert "--page-margin: 40mm;" in html


def test_export_at_page_rule_uses_margin():
    src = "---\nmargin: 40mm\n---\n\n# Title\n\nBody.\n"
    html = render_markdown(src, for_export=True)
    assert "margin: 40mm;" in html  # the @page rule
    assert "--page-margin: 40mm;" in html
