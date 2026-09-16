"""Tests for the bundled base stylesheet (typography, tables, layout)."""

from __future__ import annotations

from epy_reports._core.template import _load_base_css, _watermark_css


def test_heading_ramp_variables_defined_with_defaults():
    """Every h1-h6 color variable has a :root fallback."""
    css = _load_base_css()
    for level in range(1, 7):
        assert f"--h{level}-color:" in css
        assert f"var(--h{level}-color" in css


def test_caption_color_variable_defined():
    """--caption-color exists and figure captions use it, italicized."""
    css = _load_base_css()
    assert "--caption-color:" in css
    assert "color: var(--caption-color);" in css
    assert "font-style: italic;" in css


def test_table_header_has_accent_border():
    """The table header row gets a heading-rule accent underline."""
    css = _load_base_css()
    assert "border-bottom: 2px solid var(--heading-rule);" in css


def test_table_zebra_and_tabular_nums():
    """Zebra striping and tabular-nums are both present on tables."""
    css = _load_base_css()
    assert (
        "table tr:nth-child(even) td { background: var(--bg-stripe); }" in css
    )
    assert "font-variant-numeric: tabular-nums;" in css


def test_table_wrap_scrolls_horizontally():
    """.table-wrap allows a wide table to scroll instead of overflowing."""
    css = _load_base_css()
    assert ".table-wrap {" in css
    assert "overflow-x: auto;" in css


def test_callout_radius_is_eight():
    """Callouts use an 8px border radius."""
    css = _load_base_css()
    assert "border-radius: 8px;" in css


def test_cover_has_accent_bar():
    """The cover title carries an accent bar beneath it."""
    css = _load_base_css()
    assert "section.cover-page .cover-title::after" in css
    assert "background: var(--link);" in css


def test_toc_sticky_sidebar_scoped_to_wide_screens():
    """The sticky TOC rail only applies on screen at >=1200px."""
    css = _load_base_css()
    assert "@media screen and (min-width: 1200px)" in css
    assert "nav.toc:first-of-type" in css
    assert "position: fixed;" in css


def test_small_screen_breakpoint_present():
    """A max-width: 640px breakpoint tunes typography and spacing down."""
    css = _load_base_css()
    assert "@media (max-width: 640px)" in css


def test_epy_plotly_avoids_page_break():
    """.epy-plotly figures never split across a page break."""
    css = _load_base_css()
    assert ".epy-plotly {" in css
    assert "page-break-inside: avoid;" in css


# ---------------------------------------------------------------------------
# _watermark_css
# ---------------------------------------------------------------------------


def test_watermark_css_empty_when_no_watermark_metadata():
    """No ``watermark`` key (or a blank one) emits no CSS at all."""
    assert _watermark_css({}) == ""
    assert _watermark_css({"watermark": "   "}) == ""


def test_watermark_css_paints_screen_only_background():
    """A non-empty watermark emits a screen-scoped ::after rule."""
    css = _watermark_css({"watermark": "DRAFT"})
    assert "@media screen" in css
    assert 'url("DRAFT")' in css
    assert "opacity: 0.08" in css
    assert "filter: grayscale(1)" in css


def test_watermark_css_escapes_html_in_the_value():
    """A watermark value with quotes/angle brackets is HTML-escaped.

    The value is interpolated directly into a CSS ``url(...)`` inside an
    HTML ``<style>`` block, so an unescaped ``"`` would break out of the
    CSS string.
    """
    css = _watermark_css({"watermark": 'CONFIDENTIAL"<b>'})
    assert "&quot;" in css
    assert "&lt;b&gt;" in css
    assert '"<b>' not in css
