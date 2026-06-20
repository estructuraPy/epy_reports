"""Tests for BibEntry.short_label compact display formatting."""

from __future__ import annotations

from epy_reports.bib import BibEntry


def test_short_label_key_only():
    """With no metadata the label is just the @key."""
    entry = BibEntry(key="smith2020", type="article")
    assert entry.short_label() == "@smith2020"


def test_short_label_uses_family_name_from_comma_form():
    """A ``Family, Given`` author contributes the family name."""
    entry = BibEntry(
        key="smith2020", type="article",
        author="Smith, John", year="2020",
    )
    label = entry.short_label()
    assert "@smith2020" in label
    assert "Smith" in label
    assert "2020" in label


def test_short_label_family_name_from_space_form():
    """A ``Given Family`` author uses the last token as family."""
    entry = BibEntry(key="k", type="book", author="John Smith")
    assert "Smith" in entry.short_label()


def test_short_label_first_author_only():
    """Only the first author of an ``and`` list is shown."""
    entry = BibEntry(
        key="k", type="article",
        author="Smith, John and Doe, Jane",
    )
    label = entry.short_label()
    assert "Smith" in label
    assert "Doe" not in label


def test_short_label_truncates_long_title():
    """A long title is truncated with an ellipsis to stay compact."""
    long_title = "A" * 80
    entry = BibEntry(key="k", type="misc", title=long_title)
    label = entry.short_label()
    assert "..." in label
    assert len(label) < len(long_title) + len("@k  — ")


def test_short_label_includes_separator_when_meta_present():
    """The em-dash separator appears once metadata exists."""
    entry = BibEntry(key="k", type="misc", year="1999")
    assert "—" in entry.short_label()
