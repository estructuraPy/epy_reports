"""Tests for the graduated heading-color ramp in epyson.py."""

from __future__ import annotations

from epy_reports.epyson import _heading_ramp, _mix, load_layout_theme


def test_heading_ramp_h1_equals_header_color():
    """h1 sits at t=0 — identical to the header color."""
    ramp = _heading_ramp("#000000", "#999999")
    assert ramp["h1-color"] == "#000000"


def test_heading_ramp_h6_is_the_deepest_mix():
    """h6 sits at t=0.5 — halfway toward the muted color."""
    ramp = _heading_ramp("#000000", "#FFFFFF")
    assert ramp["h6-color"] == _mix("#000000", "#FFFFFF", 0.5)
    assert ramp["h6-color"] == "#7F7F7F"


def test_heading_ramp_is_monotonically_graduated():
    """Each level moves strictly further toward the muted color than h1."""
    ramp = _heading_ramp("#000000", "#FFFFFF")
    values = [int(ramp[f"h{i}-color"].lstrip("#")[0:2], 16) for i in range(1, 7)]
    assert values == sorted(values)
    assert values[0] < values[-1]


def test_heading_ramp_returns_all_six_levels():
    """The ramp always produces exactly h1-color..h6-color."""
    ramp = _heading_ramp("#112233", "#445566")
    assert set(ramp) == {f"h{i}-color" for i in range(1, 7)}


def test_bundled_theme_exposes_full_heading_ramp():
    """A real bundled theme's css_vars carry the computed ramp."""
    theme = load_layout_theme("corporate.epyson")
    for level in range(1, 7):
        assert f"h{level}-color" in theme.css_vars


def test_bundled_theme_h1_matches_header_color():
    """The theme's h1-color equals its header_color (t=0 of the ramp)."""
    theme = load_layout_theme("corporate.epyson")
    assert theme.css_vars["h1-color"] == theme.css_vars["heading-color"]


def test_bundled_theme_caption_color_present():
    """The theme exposes a dedicated --caption-color variable."""
    theme = load_layout_theme("corporate.epyson")
    assert "caption-color" in theme.css_vars
    assert theme.css_vars["caption-color"] == theme.css_vars["fg-muted"]
