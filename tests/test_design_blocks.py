"""Tests for the shared design-block engine (cards, big stats, ...)."""

from __future__ import annotations

from epy_reports import themes
from epy_reports._design import (
    DESIGN_BLOCK_LABELS,
    DESIGN_BLOCKS,
    DISCLOSURE_KINDS,
    DISCLOSURE_PRESETS,
    design_block,
    design_css,
    disclosure_block,
    document_css,
)

_SELECTORS = (
    ".lead",
    ".badge",
    ".card",
    ".cards",
    ".stat",
    ".stats",
    ".timeline",
    ".agenda",
    ".disclosure",
)


def test_every_block_has_label_skeleton_and_token():
    assert len(DESIGN_BLOCKS) == 8
    for kind in DESIGN_BLOCKS:
        assert kind in DESIGN_BLOCK_LABELS
        skeleton, token = design_block(kind)
        assert skeleton.strip()
        assert token
        assert token in skeleton


def test_design_block_unknown_falls_back_to_card():
    skeleton, _ = design_block("does-not-exist")
    assert ".card" in skeleton


def test_design_css_defines_component_selectors():
    theme = themes.get(themes.DEFAULT_THEME_ID)
    css = design_css(theme, scope="")
    for selector in _SELECTORS:
        assert selector in css


def test_design_css_scope_prefix_applied():
    theme = themes.get(themes.DEFAULT_THEME_ID)
    css = design_css(theme, scope=".reveal ")
    assert ".reveal .stat" in css


def test_document_css_wraps_components_with_root_vars():
    theme = themes.get(themes.DEFAULT_THEME_ID)
    css = document_css(theme)
    assert "--epy-primary" in css
    assert ".stat" in css


def test_stat_block_is_a_big_number_with_label():
    skeleton, _ = design_block("stat")
    assert "{.stat}" in skeleton
    assert "{.stat-label}" in skeleton
    assert "**42**" in skeleton


def test_disclosure_presets_render_a_disclosure_block():
    assert set(DISCLOSURE_KINDS) == set(DISCLOSURE_PRESETS)
    assert {"ai", "integrity"} <= set(DISCLOSURE_PRESETS)
    for kind in DISCLOSURE_KINDS:
        label, text = DISCLOSURE_PRESETS[kind]
        assert label and text
        skeleton, token = disclosure_block(kind)
        assert "{.disclosure}" in skeleton
        assert token in skeleton
    # Unknown kinds fall back to the AI-use disclosure.
    skeleton, _ = disclosure_block("nope")
    assert "{.disclosure}" in skeleton
