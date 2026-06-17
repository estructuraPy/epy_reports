"""Tests for index collection, heading ids and marker expansion."""

from __future__ import annotations

from epy_mdr.renderer import (
    collect_headings,
    collect_index_entries,
    render_markdown,
)


def test_figure_numbering_and_caption():
    src = (
        "![First fig](a.png){#fig-one}\n\n"
        "![Second fig](b.png){#fig-two}\n"
    )
    entries = collect_index_entries(src)
    assert entries["fig"] == [
        (1, "First fig", "fig-one"),
        (2, "Second fig", "fig-two"),
    ]


def test_table_and_equation_numbering():
    src = (
        ": A table {#tbl-a}\n\n"
        ": Another table {#tbl-b}\n\n"
        "$$\nE=mc^2\n$$ {#eq-e}\n"
    )
    entries = collect_index_entries(src)
    assert entries["tbl"] == [
        (1, "A table", "tbl-a"),
        (2, "Another table", "tbl-b"),
    ]
    assert entries["eq"] == [(1, "eq-e")]


def test_labels_inside_code_are_ignored():
    src = (
        "![Real](r.png){#fig-real}\n\n"
        "```\n"
        "![Fake](f.png){#fig-fake}\n"
        ": Fake table {#tbl-fake}\n"
        "```\n"
    )
    entries = collect_index_entries(src)
    assert entries["fig"] == [(1, "Real", "fig-real")]
    assert entries["tbl"] == []


def test_caption_prefix_stripped():
    """A caption already prefixed by the resolver is shown bare."""
    src = "![Figure 1: My cap](a.png){#fig-x}\n"
    entries = collect_index_entries(src)
    assert entries["fig"] == [(1, "My cap", "fig-x")]


def test_explicit_heading_id_kept():
    src = "## Intro {#sec-intro}\n\n### Detail\n"
    headings = collect_headings(src)
    assert headings[0] == (2, "Intro", "sec-intro")
    # Bare heading gets a generated id.
    assert headings[1][0] == 3
    assert headings[1][1] == "Detail"
    assert headings[1][2].startswith("toc-h-")


def test_headings_inside_code_ignored():
    src = "# Title\n\n```\n# Not a heading\n```\n"
    headings = collect_headings(src)
    assert len(headings) == 1
    assert headings[0][1] == "Title"


def test_render_markdown_toc_and_lof():
    src = (
        "---\ntitle: T\n---\n\n"
        "[[toc]]\n\n"
        "[[lof]]\n\n"
        "# Section A\n\n"
        "![A figure](a.png){#fig-a}\n\n"
        "See @fig-a.\n"
    )
    html = render_markdown(src)
    assert '<nav class="toc">' in html
    assert '<nav class="list-of-figures">' in html
    # TOC link resolves to the injected heading id.
    assert 'href="#toc-h-1"' in html
    # Figure list links to the figure label.
    assert 'href="#fig-a"' in html
    assert "Figure 1" in html
    # No leftover raw markers.
    assert "[[toc]]" not in html
    assert "[[lof]]" not in html


def test_render_markdown_empty_marker_collapses():
    """A list marker with no entries renders to nothing, not an error."""
    src = "---\ntitle: T\n---\n\n[[loe]]\n\nNo equations here.\n"
    html = render_markdown(src)
    assert '<nav class="list-of-equations">' not in html
    assert "[[loe]]" not in html
