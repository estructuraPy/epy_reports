"""Tests for TwoColumnDialog and ThreeColumnDialog build_markdown output."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports._ui.columns_dialog import ThreeColumnDialog, TwoColumnDialog

# ---------------------------------------------------------------------------
# Module-scoped QApplication (required for any QWidget instantiation)
# ---------------------------------------------------------------------------

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


# ---------------------------------------------------------------------------
# TwoColumnDialog tests
# ---------------------------------------------------------------------------


def test_two_col_default_split(qapp):
    """Default split is 50/50."""
    dlg = TwoColumnDialog()
    assert dlg.left_width == 50


def test_two_col_widths_sum_to_100(qapp):
    """Left and right widths always sum to 100."""
    dlg = TwoColumnDialog()
    dlg.split_spin.setValue(35)
    md = dlg.build_markdown()
    # Match only inner column fences, not the outer :::: {.columns} line.
    lines = [ln for ln in md.splitlines() if ln.startswith("::: {.column")]
    assert len(lines) == 2
    widths = [int(ln.split('width="')[1].rstrip('"%}')) for ln in lines]
    assert sum(widths) == 100


def test_two_col_left_width_in_output(qapp):
    """Left column width appears in the first .column div."""
    dlg = TwoColumnDialog()
    dlg.split_spin.setValue(60)
    md = dlg.build_markdown()
    col_lines = [ln for ln in md.splitlines() if ln.startswith("::: {.column")]
    assert 'width="60%"' in col_lines[0]


def test_two_col_right_width_is_remainder(qapp):
    """Right column width is 100 minus the left width."""
    dlg = TwoColumnDialog()
    dlg.split_spin.setValue(70)
    md = dlg.build_markdown()
    col_lines = [ln for ln in md.splitlines() if ln.startswith("::: {.column")]
    assert 'width="30%"' in col_lines[1]


def test_two_col_outer_fence(qapp):
    """Output contains the opening and closing :::: {.columns} fences."""
    dlg = TwoColumnDialog()
    md = dlg.build_markdown()
    assert ":::: {.columns}" in md
    assert "::::" in md


def test_two_col_two_inner_fences(qapp):
    """Exactly two inner ::: {.column ...} fences are present."""
    dlg = TwoColumnDialog()
    md = dlg.build_markdown()
    inner = [ln for ln in md.splitlines() if ln.startswith("::: {.column")]
    assert len(inner) == 2


def test_two_col_custom_text(qapp):
    """User-supplied text appears in the output."""
    dlg = TwoColumnDialog()
    dlg.left_edit.setPlainText("Left body")
    dlg.right_edit.setPlainText("Right body")
    md = dlg.build_markdown()
    assert "Left body" in md
    assert "Right body" in md


def test_two_col_placeholder_fallback(qapp):
    """Empty text fields fall back to placeholder strings."""
    dlg = TwoColumnDialog()
    dlg.left_edit.setPlainText("")
    dlg.right_edit.setPlainText("")
    md = dlg.build_markdown()
    assert "Left column content" in md
    assert "Right column content" in md


def test_two_col_leading_blank_line(qapp):
    """build_markdown output starts with a blank line."""
    dlg = TwoColumnDialog()
    md = dlg.build_markdown()
    assert md.startswith("\n")


def test_two_col_trailing_newline(qapp):
    """build_markdown output ends with a newline."""
    dlg = TwoColumnDialog()
    md = dlg.build_markdown()
    assert md.endswith("\n")


# ---------------------------------------------------------------------------
# ThreeColumnDialog tests
# ---------------------------------------------------------------------------


def test_three_col_default_widths(qapp):
    """Default widths are 33/33/34."""
    dlg = ThreeColumnDialog()
    assert dlg.width1 == 33
    assert dlg.width2 == 33
    assert dlg.width3 == 34


def test_three_col_third_width_is_remainder(qapp):
    """Third column width is always 100 - w1 - w2."""
    dlg = ThreeColumnDialog()
    dlg.w1_spin.setValue(40)
    dlg.w2_spin.setValue(40)
    assert dlg.width3 == 20


def test_three_col_third_width_clamped(qapp):
    """Third column width is clamped to a minimum of 5 %."""
    dlg = ThreeColumnDialog()
    dlg.w1_spin.setValue(60)
    dlg.w2_spin.setValue(60)
    assert dlg.width3 == 5


def test_three_col_three_inner_fences(qapp):
    """Exactly three inner ::: {.column ...} fences are present."""
    dlg = ThreeColumnDialog()
    md = dlg.build_markdown()
    inner = [ln for ln in md.splitlines() if ln.startswith("::: {.column")]
    assert len(inner) == 3


def test_three_col_widths_in_output(qapp):
    """All three widths appear in the column div attributes."""
    dlg = ThreeColumnDialog()
    dlg.w1_spin.setValue(25)
    dlg.w2_spin.setValue(50)
    md = dlg.build_markdown()
    assert 'width="25%"' in md
    assert 'width="50%"' in md
    assert 'width="25%"' in md  # third = 100-25-50=25


def test_three_col_outer_fence(qapp):
    """Output contains the opening and closing :::: {.columns} fences."""
    dlg = ThreeColumnDialog()
    md = dlg.build_markdown()
    assert ":::: {.columns}" in md
    assert "::::" in md


def test_three_col_custom_text(qapp):
    """User-supplied text for all three columns appears in the output."""
    dlg = ThreeColumnDialog()
    dlg.col1_edit.setPlainText("Alpha")
    dlg.col2_edit.setPlainText("Beta")
    dlg.col3_edit.setPlainText("Gamma")
    md = dlg.build_markdown()
    assert "Alpha" in md
    assert "Beta" in md
    assert "Gamma" in md


def test_three_col_placeholder_fallback(qapp):
    """Empty text fields fall back to placeholder strings."""
    dlg = ThreeColumnDialog()
    dlg.col1_edit.setPlainText("")
    dlg.col2_edit.setPlainText("")
    dlg.col3_edit.setPlainText("")
    md = dlg.build_markdown()
    assert "Column 1 content" in md
    assert "Column 2 content" in md
    assert "Column 3 content" in md


def test_three_col_leading_blank_line(qapp):
    """build_markdown output starts with a blank line."""
    dlg = ThreeColumnDialog()
    md = dlg.build_markdown()
    assert md.startswith("\n")


def test_three_col_trailing_newline(qapp):
    """build_markdown output ends with a newline."""
    dlg = ThreeColumnDialog()
    md = dlg.build_markdown()
    assert md.endswith("\n")


# ---------------------------------------------------------------------------
# Render integration test: fenced-divs produce .columns/.column HTML
# ---------------------------------------------------------------------------


def test_two_col_renders_to_html(qapp):
    """Two-column block renders to HTML with div.columns and column content."""
    from epy_reports._core.renderer import render_markdown

    dlg = TwoColumnDialog()
    dlg.left_edit.setPlainText("Left text")
    dlg.right_edit.setPlainText("Right text")
    md = dlg.build_markdown()
    html = render_markdown(md)
    # Pandoc emits the outer fence as div.columns, inner fences as div.column.
    assert 'class="columns"' in html
    assert "Left text" in html
    assert "Right text" in html


def test_three_col_renders_to_html(qapp):
    """Three-column block renders to HTML with content from all three cols."""
    from epy_reports._core.renderer import render_markdown

    dlg = ThreeColumnDialog()
    dlg.col1_edit.setPlainText("ColAlpha")
    dlg.col2_edit.setPlainText("ColBeta")
    dlg.col3_edit.setPlainText("ColGamma")
    md = dlg.build_markdown()
    html = render_markdown(md)
    assert 'class="columns"' in html
    assert "ColAlpha" in html
    assert "ColBeta" in html
    assert "ColGamma" in html
