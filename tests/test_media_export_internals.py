"""Tests for the DOCX/diagram media-export internals.

Covers the offscreen diagram page builder and the component-simplification
branches the existing test_media_export.py does not reach.
"""

from __future__ import annotations

from pathlib import Path

from epy_reports._core._media_export import (
    _diagram_page_html,
    collect_diagrams,
    render_diagram_pngs,
    simplify_components_for_export,
)

# ---------------------------------------------------------------------------
# simplify_components_for_export — extra branches
# ---------------------------------------------------------------------------


def test_timeline_wrapper_is_unwrapped():
    """A timeline component keeps its list but drops the wrapper."""
    src = (
        "::: {.timeline}\n"
        "- First\n- Second\n"
        ":::\n"
    )
    out = simplify_components_for_export(src)
    assert "- First" in out
    assert ".timeline" not in out


def test_agenda_wrapper_is_unwrapped():
    """An agenda component keeps its list but drops the wrapper."""
    src = "::: {.agenda}\n- Item A\n- Item B\n:::\n"
    out = simplify_components_for_export(src)
    assert "- Item A" in out
    assert ".agenda" not in out


def test_fenced_code_is_passed_through_untouched():
    """Content inside a code fence is never rewritten."""
    src = "```text\n::: {.cards}\n:::\n```\n"
    out = simplify_components_for_export(src)
    assert "::: {.cards}" in out  # untouched because it is inside a fence


def test_trailing_newline_preserved():
    """A source ending in a newline keeps it after rewriting."""
    src = "plain paragraph\n"
    assert simplify_components_for_export(src).endswith("\n")


# ---------------------------------------------------------------------------
# _diagram_page_html
# ---------------------------------------------------------------------------


def test_diagram_page_html_embeds_mermaid_engine():
    """A mermaid diagram pulls in the mermaid init + a themed pre."""
    diagrams = [("mermaid", "flowchart LR\nA-->B")]
    html = _diagram_page_html(diagrams, theme_css="body{color:red}")
    assert "window._epy_init_mermaid()" in html
    assert '<pre class="mermaid">' in html
    assert "body{color:red}" in html


def test_diagram_page_html_embeds_nomnoml_engine():
    """A nomnoml diagram pulls in the nomnoml init."""
    diagrams = [("nomnoml", "[A] -> [B]")]
    html = _diagram_page_html(diagrams, theme_css="")
    assert "window._epy_init_nomnoml()" in html
    assert '<pre class="nomnoml">' in html


def test_diagram_page_html_escapes_body():
    """Diagram bodies are HTML-escaped inside the page."""
    diagrams = [("mermaid", "A & <B>")]
    html = _diagram_page_html(diagrams, theme_css="")
    assert "&amp;" in html
    assert "&lt;B&gt;" in html


def test_collect_diagrams_handles_attribute_fences():
    """An attribute-style ```{.mermaid} fence is recognised."""
    src = "```{.mermaid}\nflowchart LR\nA-->B\n```\n"
    assert collect_diagrams(src) == [("mermaid", "flowchart LR\nA-->B")]


# ---------------------------------------------------------------------------
# render_diagram_pngs — early-return paths (no event loop driven)
# ---------------------------------------------------------------------------


def test_render_diagram_pngs_empty_returns_empty(tmp_path: Path):
    """No diagrams yields no PNG results."""
    assert render_diagram_pngs([], tmp_path) == []


def test_render_diagram_pngs_without_qapplication(tmp_path, monkeypatch):
    """With no running QApplication every diagram returns None."""
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication, "instance", staticmethod(
        lambda: None
    ))
    out = render_diagram_pngs(
        [("mermaid", "flowchart LR\nA-->B")], tmp_path
    )
    assert out == [None]
