"""Tests for the shared design-block engine (cards, big stats, ...)."""

from __future__ import annotations

from epy_reports import themes
from epy_reports._design import (
    DESIGN_BLOCK_LABELS,
    DESIGN_BLOCKS,
    design_block,
    design_css,
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
