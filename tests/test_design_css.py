"""Tests for the theme-driven design component CSS."""

from __future__ import annotations

from epy_editor_kit.themes_base import Theme

from epy_reports._design import design_css, document_css

_THEME = Theme(
    id="t",
    display_name="T",
    qt_palette={},
    css_vars={
        "bg": "#ffffff",
        "fg": "#222222",
        "heading-color": "#003366",
        "link": "#2a76dd",
        "border": "#d0d0d0",
        "bg-soft": "#f3f3f3",
        "font-family-headings": "Georgia",
    },
)


def test_design_css_uses_theme_colors():
    """The accent/border colours come from the theme css_vars."""
    css = design_css(_THEME)
    assert "#2a76dd" in css  # primary / link
    assert "#d0d0d0" in css  # border


def test_design_css_scope_prefix_applied():
    """A scope prefix is applied to every component selector."""
    css = design_css(_THEME, scope=".reveal ")
    assert ".reveal .card {" in css
    assert ".reveal .badge {" in css


def test_design_css_no_scope_bare_selectors():
    """An empty scope leaves bare selectors."""
    css = design_css(_THEME, scope="")
    assert "\n.card {" in css


def test_design_css_falls_back_to_defaults():
    """A theme with no css_vars still produces valid CSS via defaults."""
    bare = Theme("b", "B", {}, {})
    css = design_css(bare)
    assert ".card {" in css
    assert "#2a76dd" in css  # default primary


def test_document_css_includes_epy_aliases():
    """The document CSS exposes the ``--epy-*`` alias block."""
    css = document_css(_THEME)
    assert "--epy-primary: var(--link);" in css
    assert "--epy-border: var(--border);" in css


def test_document_css_includes_root_vars():
    """The document CSS embeds the theme's :root variables."""
    css = document_css(_THEME)
    assert "--bg: #ffffff;" in css
    assert ".card {" in css
