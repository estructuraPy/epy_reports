"""Tests for the IMAGE_MARKDOWN quick-insert snippet."""

from __future__ import annotations

from epy_reports._core import snippets


def test_image_markdown_includes_width():
    """The formatted snippet carries the chosen width attribute."""
    md = snippets.IMAGE_MARKDOWN.format(
        caption="Beam", path="figures/beam.png", label="3", width="80%"
    )
    assert md == "![Beam](figures/beam.png){#fig-3 width=80%}"
    assert "width=80%" in md


def test_image_markdown_custom_width():
    """A pixel width is passed through unchanged."""
    md = snippets.IMAGE_MARKDOWN.format(
        caption="Plan", path="figures/plan.svg", label="1", width="300px"
    )
    assert "width=300px" in md
    assert md == "![Plan](figures/plan.svg){#fig-1 width=300px}"
