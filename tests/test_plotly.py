"""Tests for the plotly fenced-block expansion helpers."""

from __future__ import annotations

from epy_reports._plotly import (
    expand_plotly,
    has_plotly,
    strip_plotly_for_export,
)
from epy_reports.renderer import _wrap_wide_tables

_SPEC = '{"data": [{"type": "bar", "y": [1, 2, 3]}], "layout": {}}'
_FENCE = (
    "```{.plotly fallback=figs/drift.png height=300px}\n"
    f"{_SPEC}\n```\n"
)
_FENCE_NO_FALLBACK = f"```plotly\n{_SPEC}\n```\n"


def test_expand_plotly_interactive_produces_div_and_script():
    """A plotly fence becomes a div + JSON script pair by default."""
    out = expand_plotly(_FENCE)
    assert '<div class="epy-plotly" id="epy-plotly-0"' in out
    assert 'style="height: 300px;"' in out
    assert (
        '<script type="application/json" '
        'data-plotly-for="epy-plotly-0">'
    ) in out
    assert '"type": "bar"' in out


def test_expand_plotly_default_height_when_unset():
    """A fence without height= falls back to the default height."""
    out = expand_plotly(_FENCE_NO_FALLBACK)
    assert 'style="height: 420px;"' in out


def test_expand_plotly_escapes_script_close_tag():
    """A literal </script> inside the JSON payload cannot break out."""
    spec = '{"data": [], "layout": {"title": "</script><script>bad"}}'
    src = f"```{{.plotly}}\n{spec}\n```\n"
    out = expand_plotly(src)
    assert "</script><script>bad" not in out
    assert "<\\/script><script>bad" in out


def test_expand_plotly_static_uses_fallback_image():
    """static=True degrades a fence with fallback= to a plain image."""
    out = expand_plotly(_FENCE, static=True)
    assert out.strip() == "![](figs/drift.png)"
    assert "epy-plotly" not in out


def test_expand_plotly_static_without_fallback_stays_interactive():
    """A fence without fallback= stays interactive under static=True."""
    out = expand_plotly(_FENCE_NO_FALLBACK, static=True)
    assert 'class="epy-plotly"' in out


def test_expand_plotly_leaves_plain_code_untouched():
    """A plain ```python fence is not treated as a plotly figure."""
    src = "```python\nprint('hi')\n```\n"
    assert expand_plotly(src) == src


def test_expand_plotly_multiple_fences_get_sequential_ids():
    """Multiple fences in one document get distinct, ordered ids."""
    out = expand_plotly(_FENCE + "\n" + _FENCE_NO_FALLBACK)
    assert 'id="epy-plotly-0"' in out
    assert 'id="epy-plotly-1"' in out


def test_has_plotly_true_when_interactive_div_present():
    """has_plotly() is True once a fence has been expanded."""
    out = expand_plotly(_FENCE)
    assert has_plotly(out) is True


def test_has_plotly_false_when_fully_static():
    """has_plotly() is False once every fence became a fallback image."""
    out = expand_plotly(_FENCE, static=True)
    assert has_plotly(out) is False


def test_has_plotly_false_for_plain_text():
    """A document with no plotly fences reports no interactive figures."""
    assert has_plotly("# Heading\n\nBody text.\n") is False


def test_strip_plotly_for_export_uses_fallback_image():
    """DOCX export replaces a fence carrying fallback= with the image."""
    out = strip_plotly_for_export(_FENCE)
    assert out.strip() == "![](figs/drift.png)"


def test_strip_plotly_for_export_note_without_fallback():
    """A fallback-less fence becomes a note paragraph for DOCX export."""
    out = strip_plotly_for_export(_FENCE_NO_FALLBACK)
    assert "Interactive figure" in out
    assert "epy-plotly" not in out


# ---------------------------------------------------------------------------
# _wrap_wide_tables (renderer.py) — shipped alongside the plotly pipeline.
# ---------------------------------------------------------------------------

_TABLE_HTML = (
    "<table><thead><tr><th>A</th></tr></thead>"
    "<tbody><tr><td>1</td></tr></tbody></table>"
)


def test_wrap_wide_tables_adds_wrapper():
    """A bare <table> gets wrapped in a scrollable .table-wrap div."""
    out = _wrap_wide_tables(_TABLE_HTML)
    assert out == f'<div class="table-wrap">{_TABLE_HTML}</div>'


def test_wrap_wide_tables_is_idempotent():
    """Wrapping an already-wrapped table does not nest a second one."""
    once = _wrap_wide_tables(_TABLE_HTML)
    twice = _wrap_wide_tables(once)
    assert once == twice
    assert twice.count("table-wrap") == 1


def test_wrap_wide_tables_no_table_is_noop():
    """A body with no <table> is returned unchanged."""
    body = "<p>No tables here.</p>"
    assert _wrap_wide_tables(body) == body


def test_wrap_wide_tables_wraps_each_of_several_tables():
    """Multiple sibling tables each get their own wrapper."""
    body = _TABLE_HTML + "\n" + _TABLE_HTML
    out = _wrap_wide_tables(body)
    assert out.count('<div class="table-wrap">') == 2
