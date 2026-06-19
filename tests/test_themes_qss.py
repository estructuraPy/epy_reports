"""Tests for tonal QSS generation across all 9 themes.

Validates that:
- qss_for() returns a non-empty string for every theme.
- Every hex colour emitted inside the stylesheet is a valid 6-digit
  #RRGGBB code (no truncation or arithmetic overflow).
- Each theme produces at least the key tonal-derived colours
  (bg_toolbar, accent_soft) that differ from the raw window background.
- The colour-math helpers (_hex_to_rgb, _mix, _lighten, _darken,
  _is_dark) behave correctly as pure functions.

No Qt display is required: these tests run headlessly.
"""

from __future__ import annotations

import re

import pytest

from epy_mdr.epyson import (
    _darken,
    _hex_to_rgb,
    _is_dark,
    _lighten,
    _mix,
    _tonal_variants,
    qss_for,
)
from epy_mdr.themes import THEMES

_HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")
# Qt also accepts 8-digit (#RRGGBBAA); we only emit 6-digit codes.
_BAD_HEX_RE = re.compile(r"#[0-9A-Fa-f]{1,5}\b|#[0-9A-Fa-f]{7}\b")


# ---------------------------------------------------------------------------
# Colour-math unit tests
# ---------------------------------------------------------------------------


def test_hex_to_rgb_white():
    assert _hex_to_rgb("#FFFFFF") == (255, 255, 255)


def test_hex_to_rgb_black():
    assert _hex_to_rgb("#000000") == (0, 0, 0)


def test_hex_to_rgb_lower():
    assert _hex_to_rgb("#ff0000") == (255, 0, 0)


def test_mix_zero_returns_c1():
    assert _mix("#FF0000", "#0000FF", 0.0) == "#FF0000"


def test_mix_one_returns_c2():
    assert _mix("#FF0000", "#0000FF", 1.0) == "#0000FF"


def test_mix_half():
    result = _mix("#000000", "#FFFFFF", 0.5)
    r, g, b = _hex_to_rgb(result)
    assert 120 <= r <= 136
    assert 120 <= g <= 136
    assert 120 <= b <= 136


def test_lighten_black():
    """Lighten pure black by 50% should yield a mid-grey."""
    result = _lighten("#000000", 0.5)
    r, g, b = _hex_to_rgb(result)
    assert r == g == b
    assert 120 <= r <= 136


def test_darken_white():
    """Darken pure white by 10% should yield a very light grey."""
    result = _darken("#FFFFFF", 0.1)
    r, g, b = _hex_to_rgb(result)
    assert r == g == b
    assert 220 <= r <= 235


def test_is_dark_black():
    assert _is_dark("#000000") is True


def test_is_dark_white():
    assert _is_dark("#FFFFFF") is False


def test_is_dark_mid_grey():
    # #888888 linear luminance ≈ 0.533 > 0.5 → not dark
    assert _is_dark("#888888") is False
    # #666666 linear luminance ≈ 0.133 < 0.5 → dark
    assert _is_dark("#666666") is True


# ---------------------------------------------------------------------------
# _tonal_variants — structural sanity
# ---------------------------------------------------------------------------


def test_tonal_variants_light_keys():
    tv = _tonal_variants("#FFFFFF", "#0066CC", is_dark_theme=False)
    expected = {
        "bg_toolbar", "bg_statusbar", "bg_panel",
        "bg_menu", "accent_soft", "accent_strong", "scrollbar_handle",
    }
    assert set(tv.keys()) == expected


def test_tonal_variants_all_hex():
    tv = _tonal_variants("#FFFFFF", "#0066CC", is_dark_theme=False)
    for key, val in tv.items():
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", val), (
            f"{key}={val!r} is not a valid 6-digit hex"
        )


def test_tonal_variants_toolbar_darker_on_light():
    """Toolbar should be darker than the window bg on light themes."""
    tv = _tonal_variants("#FFFFFF", "#0066CC", is_dark_theme=False)
    r_win = 255
    r_tb, _, _ = _hex_to_rgb(tv["bg_toolbar"])
    assert r_tb < r_win, "toolbar should be darker than window on light"


def test_tonal_variants_toolbar_lighter_on_dark():
    """Toolbar should be lighter than the window bg on dark themes."""
    dark_bg = "#1E1E1E"
    tv = _tonal_variants(dark_bg, "#569CD6", is_dark_theme=True)
    r_win, _, _ = _hex_to_rgb(dark_bg)
    r_tb, _, _ = _hex_to_rgb(tv["bg_toolbar"])
    assert r_tb > r_win, "toolbar should be lighter than window on dark"


# ---------------------------------------------------------------------------
# qss_for — all 9 themes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("theme_id", sorted(THEMES.keys()))
def test_qss_non_empty(theme_id: str):
    """qss_for returns a non-empty string for every theme."""
    theme = THEMES[theme_id]
    qss = qss_for(theme)
    assert isinstance(qss, str)
    assert len(qss.strip()) > 200, (
        f"QSS for {theme_id!r} is unexpectedly short"
    )


@pytest.mark.parametrize("theme_id", sorted(THEMES.keys()))
def test_qss_no_malformed_hex(theme_id: str):
    """All hex codes emitted in the QSS are valid 6-digit #RRGGBB."""
    theme = THEMES[theme_id]
    qss = qss_for(theme)
    bad = _BAD_HEX_RE.findall(qss)
    assert not bad, (
        f"Malformed hex codes in QSS for {theme_id!r}: {bad}"
    )


@pytest.mark.parametrize("theme_id", sorted(THEMES.keys()))
def test_qss_contains_theme_colors(theme_id: str):
    """The Fluent QSS embeds the theme accent and a derived neutral fill."""
    theme = THEMES[theme_id]
    qss = qss_for(theme)
    window = theme.qt_palette.get("Window", "#FFFFFF")
    text = theme.qt_palette.get("WindowText", "#000000")
    highlight = theme.qt_palette.get("Highlight", "#0066CC")
    subtle = _mix(text, window, 0.94)

    assert highlight.upper() in qss.upper(), (
        f"accent {highlight!r} not found in QSS for {theme_id!r}"
    )
    assert subtle.upper() in qss.upper(), (
        f"subtle fill {subtle!r} not found in QSS for {theme_id!r}"
    )


@pytest.mark.parametrize("theme_id", sorted(THEMES.keys()))
def test_qss_key_widgets_present(theme_id: str):
    """QSS covers the main widget types that need tonal styling."""
    theme = THEMES[theme_id]
    qss = qss_for(theme)
    for widget in (
        "QToolBar",
        "QToolButton",
        "QTabBar",
        "QMenu",
        "QStatusBar",
        "QScrollBar",
    ):
        assert widget in qss, (
            f"{widget} selector missing in QSS for {theme_id!r}"
        )
