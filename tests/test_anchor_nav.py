"""Tests for in-page anchor navigation under a ``<base href>``.

With a ``<base>`` pointing at the document directory (live preview), a
plain ``href="#id"`` resolves against the base and navigates the preview
away — TOC entries and Figure/Table/Equation cross-references silently
break. The template injects an interceptor exactly when a ``<base>`` is
emitted; relocatable exports (``embed_images=True``) drop both.
"""

from __future__ import annotations

from epy_reports._core.renderer import render_markdown
from epy_reports._core.template import build_html_document

_MARKER = "epyAnchor"


def test_preview_with_base_ships_anchor_interceptor(tmp_path):
    html = build_html_document(
        body="<p><a href='#sec-x'>jump</a></p>",
        base_dir=tmp_path,
        title="T",
    )
    assert "<base href=" in html
    assert _MARKER in html


def test_embedded_export_has_no_base_and_no_interceptor(tmp_path):
    html = build_html_document(
        body="<p><a href='#sec-x'>jump</a></p>",
        base_dir=tmp_path,
        title="T",
        embed_images=True,
    )
    assert "<base href=" not in html
    assert _MARKER not in html


def test_no_base_dir_means_no_interceptor():
    html = build_html_document(
        body="<p>x</p>", base_dir=None, title="T"
    )
    assert "<base href=" not in html
    assert _MARKER not in html


def test_interceptor_records_scroll_for_back_navigation(tmp_path):
    """The script pushes history state so Back restores the position."""
    html = build_html_document(
        body="<p>x</p>", base_dir=tmp_path, title="T"
    )
    assert "history.pushState" in html
    assert "epyScroll" in html
    assert "popstate" in html


def test_render_markdown_preview_path_carries_interceptor(tmp_path):
    """End-to-end: the preview HTML (base_dir set) ships the fix."""
    html = render_markdown(
        "## Intro {#sec-intro}\n\nSee @sec-intro.\n", base_dir=tmp_path
    )
    assert _MARKER in html
