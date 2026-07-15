"""Tests for the snippets module: labels and YAML front-matter helpers."""

from __future__ import annotations

from epy_reports import snippets
from epy_reports.snippets import (
    find_labels,
    parse_front_matter,
    parse_header_cells,
    set_metadata_field,
)

# ---------------------------------------------------------------------------
# find_labels
# ---------------------------------------------------------------------------


def test_find_labels_extracts_each_kind():
    """One label of each kind is extracted with its kind."""
    text = (
        "![cap](x.png){#fig-a}\n"
        ": cap {#tbl-b}\n"
        "$$x$$ {#eq-c}\n"
        "## H {#sec-d}\n"
    )
    labels = find_labels(text)
    kinds = {label.kind for label in labels}
    assert kinds == {"fig", "tbl", "eq", "sec"}


def test_find_labels_dedupes_in_order():
    """Repeated labels are de-duplicated, first occurrence wins order."""
    text = "{#fig-a}\n{#fig-b}\n{#fig-a}\n"
    names = [label.name for label in find_labels(text)]
    assert names == ["fig-a", "fig-b"]


def test_find_labels_ignores_non_crossref_braces():
    """Plain attribute braces without a known kind are ignored."""
    assert find_labels("text {#other-thing} more") == []


# ---------------------------------------------------------------------------
# parse_front_matter
# ---------------------------------------------------------------------------


def test_parse_front_matter_reads_scalars():
    """Top-level scalars are parsed; quotes are stripped."""
    text = '---\ntitle: "My Doc"\nauthor: ANM\n---\n\nBody\n'
    meta = parse_front_matter(text)
    assert meta["title"] == "My Doc"
    assert meta["author"] == "ANM"


def test_parse_front_matter_no_block():
    """A document without front matter yields an empty dict."""
    assert parse_front_matter("# Heading\n") == {}


def test_parse_front_matter_skips_indented_and_comments():
    """Indented lines and comments are ignored."""
    text = "---\ntitle: T\n# a comment\n  nested: x\n---\n"
    meta = parse_front_matter(text)
    assert meta == {"title": "T"}


# ---------------------------------------------------------------------------
# parse_header_cells
# ---------------------------------------------------------------------------


def test_parse_header_cells_from_list():
    """A real list is normalised to strings."""
    assert parse_header_cells(["A", "B"]) == ["A", "B"]


def test_parse_header_cells_from_json_string():
    """A JSON flow-sequence string is parsed into cells."""
    assert parse_header_cells('["A", "B", "C"]') == ["A", "B", "C"]


def test_parse_header_cells_plain_string_single_cell():
    """A plain string becomes a single-cell list."""
    assert parse_header_cells("Just text") == ["Just text"]


def test_parse_header_cells_empty():
    """Empty / falsey values yield an empty list."""
    assert parse_header_cells("") == []
    assert parse_header_cells(None) == []


def test_parse_header_cells_malformed_json_is_single_cell():
    """A bracketed but invalid JSON string falls back to one cell."""
    assert parse_header_cells("[not, valid") == ["[not, valid"]


# ---------------------------------------------------------------------------
# set_metadata_field
# ---------------------------------------------------------------------------


def test_set_metadata_creates_block_when_absent():
    """Setting a field on a bare doc prepends a front-matter block."""
    out = set_metadata_field("# Body\n", "title", "T")
    assert out.startswith("---\ntitle: T\n---\n")
    assert "# Body" in out


def test_set_metadata_replaces_existing_field():
    """An existing field is replaced in place, not duplicated."""
    text = "---\ntitle: Old\n---\n\nBody\n"
    out = set_metadata_field(text, "title", "New")
    assert "title: New" in out
    assert "title: Old" not in out
    assert out.count("title:") == 1


def test_set_metadata_appends_new_field_to_block():
    """A new field is appended to the existing block."""
    text = "---\ntitle: T\n---\n\nBody\n"
    out = set_metadata_field(text, "author", "ANM")
    assert "title: T" in out
    assert "author: ANM" in out


def test_set_metadata_quotes_ambiguous_value():
    """A value with a colon is quoted to stay valid YAML."""
    out = set_metadata_field("# B\n", "subtitle", "Part 1: Intro")
    assert 'subtitle: "Part 1: Intro"' in out


def test_set_metadata_raw_value_written_verbatim():
    """A raw value (e.g. a flow sequence) is not quoted."""
    out = set_metadata_field("# B\n", "header", '["A", "B"]', raw=True)
    assert 'header: ["A", "B"]' in out


# ---------------------------------------------------------------------------
# Template constants sanity
# ---------------------------------------------------------------------------


def test_callout_templates_cover_all_kinds():
    """A template exists for every callout kind."""
    assert set(snippets.CALLOUT_TEMPLATES) == {
        "note", "tip", "warning", "important", "caution"
    }


def test_kind_descriptions_cover_label_kinds():
    """Each cross-ref kind has a human description."""
    assert set(snippets.KIND_DESCRIPTIONS) == {"fig", "tbl", "eq", "sec"}
