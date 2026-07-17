"""Tests for the theme-driven design component CSS."""

from __future__ import annotations

from epy_reports._design import design_css, document_css
from epy_reports.themes_base import Theme

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


# ---------------------------------------------------------------------------
# verdict / checklist / status pills
# ---------------------------------------------------------------------------


def test_document_css_includes_status_aliases():
    """The document CSS exposes --epy-pass/-fail/-warn aliased to callouts."""
    css = document_css(_THEME)
    assert "--epy-pass: var(--callout-tip-border);" in css
    assert "--epy-fail: var(--callout-caution-border);" in css
    assert "--epy-warn: var(--callout-warning-border);" in css


def test_design_css_defines_badge_status_pills():
    """.badge.pass/.fail/.warn override the base badge background."""
    css = design_css(_THEME)
    assert ".badge.pass {" in css
    assert ".badge.fail {" in css
    assert ".badge.warn {" in css


def test_design_css_defines_verdict_banner():
    """.verdict and its .pass/.fail/.warn variants are defined."""
    css = design_css(_THEME)
    assert ".verdict {" in css
    assert ".verdict.pass {" in css
    assert ".verdict.fail {" in css
    assert ".verdict.warn {" in css


def test_design_css_defines_checklist_task_list():
    """.checklist styles the Pandoc task-list markup."""
    css = design_css(_THEME)
    assert ".checklist li {" in css
    assert 'input[type="checkbox"]' in css


def test_design_css_verdict_checklist_scope_prefix_applied():
    """The scope prefix reaches the verdict/checklist selectors too."""
    css = design_css(_THEME, scope=".reveal ")
    assert ".reveal .verdict {" in css
    assert ".reveal .checklist li {" in css
