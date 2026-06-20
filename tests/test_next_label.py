"""Tests for the next_label_suffix pure function."""

from __future__ import annotations

from epy_reports.tab import next_label_suffix


def test_empty_text_returns_one():
    """Empty buffer gives suffix '1' for any kind."""
    assert next_label_suffix("", "fig") == "1"
    assert next_label_suffix("", "tbl") == "1"
    assert next_label_suffix("", "eq") == "1"


def test_sequential_after_existing():
    """With {#fig-1}{#fig-2}, returns '3'."""
    text = "![a](a.png){#fig-1 width=80%}\n![b](b.png){#fig-2 width=80%}"
    assert next_label_suffix(text, "fig") == "3"


def test_non_integer_suffixes_ignored():
    """Non-integer suffixes like 'capacity' are ignored; returns '1'."""
    text = "![a](a.png){#fig-capacity width=80%}"
    assert next_label_suffix(text, "fig") == "1"


def test_mixed_int_and_non_int():
    """When both int and non-int suffixes are present, max int wins."""
    text = (
        "![a](a.png){#fig-capacity width=80%}\n"
        "![b](b.png){#fig-2 width=80%}"
    )
    assert next_label_suffix(text, "fig") == "3"


def test_per_kind_independence():
    """fig labels do not affect tbl suffix computation."""
    text = "![a](a.png){#fig-1 width=80%}"
    assert next_label_suffix(text, "tbl") == "1"


def test_gaps_use_max():
    """Non-contiguous sequence: {#fig-1}{#fig-5} returns '6'."""
    text = "![a](a.png){#fig-1 width=80%}\n![b](b.png){#fig-5 width=80%}"
    assert next_label_suffix(text, "fig") == "6"


def test_eq_kind():
    """Equation labels counted independently."""
    text = "$$ y=x $$ {#eq-1}\n$$ z=w $$ {#eq-3}"
    assert next_label_suffix(text, "eq") == "4"
