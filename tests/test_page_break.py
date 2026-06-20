"""Tests for the [[pagebreak]] marker expansion."""

from __future__ import annotations

from epy_reports.renderer import render_markdown


def test_pagebreak_marker_renders_div():
    src = (
        "---\ntitle: T\n---\n\n"
        "First page.\n\n"
        "[[pagebreak]]\n\n"
        "Second page.\n"
    )
    html = render_markdown(src)
    assert '<div class="page-break"></div>' in html
    assert "[[pagebreak]]" not in html


def test_pagebreak_case_insensitive_and_spaced():
    src = "---\ntitle: T\n---\n\n[[ PageBreak ]]\n"
    html = render_markdown(src)
    assert '<div class="page-break"></div>' in html


def test_pagebreak_inside_code_block_untouched():
    src = (
        "---\ntitle: T\n---\n\n"
        "```\n[[pagebreak]]\n```\n"
    )
    html = render_markdown(src)
    # The literal marker survives inside the code block.
    assert "[[pagebreak]]" in html
