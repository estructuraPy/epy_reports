"""Tests for selectable page size (preview class + dimensions + layout)."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QPageSize
from PySide6.QtWidgets import QApplication

from epy_reports._core.renderer import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZES,
    normalize_page_size,
    page_size_dimensions,
    render_markdown,
)

_SRC = "# Title\n\nBody paragraph.\n"

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


# ---------------------------------------------------------------------------
# render_markdown emits the size class on the body
# ---------------------------------------------------------------------------

def test_paged_letter_emits_size_class():
    """``page_size='letter'`` yields ``paged size-letter`` body class."""
    html = render_markdown(_SRC, paged=True, page_size="letter")
    assert '<body class="paged size-letter">' in html


def test_paged_a4_emits_size_class():
    """``page_size='a4'`` yields a ``size-a4`` body class."""
    html = render_markdown(_SRC, paged=True, page_size="a4")
    assert '<body class="paged size-a4">' in html


def test_paged_unknown_falls_back_to_letter():
    """An unknown page size normalizes to ``size-letter``."""
    html = render_markdown(_SRC, paged=True, page_size="tabloid")
    assert '<body class="paged size-letter">' in html


def test_default_page_size_is_letter():
    """Missing ``page_size`` defaults to ``size-letter``."""
    html = render_markdown(_SRC, paged=True)
    assert '<body class="paged size-letter">' in html


def test_size_class_emitted_even_when_not_paged():
    """The size class is always present, even without paged mode."""
    html = render_markdown(_SRC, page_size="legal")
    assert '<body class="size-legal">' in html
    assert "paged" not in html.split("<body", 1)[1].split(">", 1)[0]


# ---------------------------------------------------------------------------
# normalizer / dimension lookup
# ---------------------------------------------------------------------------

def test_normalize_defaults_to_letter():
    """Missing / empty values normalize to the Letter default."""
    assert normalize_page_size(None) == "letter"
    assert normalize_page_size("") == "letter"
    assert DEFAULT_PAGE_SIZE == "letter"


def test_normalize_is_case_insensitive():
    """Case and surrounding whitespace are ignored."""
    assert normalize_page_size("  A4 ") == "a4"
    assert normalize_page_size("LEGAL") == "legal"


def test_normalize_junk_falls_back_to_letter():
    """Unknown values fall back to Letter."""
    assert normalize_page_size("tabloid") == "letter"


def test_dimension_lookup():
    """Each key maps to its correct ``(width_mm, height_mm)``."""
    assert page_size_dimensions("letter") == (215.9, 279.4)
    assert page_size_dimensions("a4") == (210.0, 297.0)
    assert page_size_dimensions("legal") == (215.9, 355.6)
    assert page_size_dimensions("junk") == PAGE_SIZES["letter"]


# ---------------------------------------------------------------------------
# export page-layout helper returns the expected QPageSize.PageSizeId
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("key", "expected_id"),
    [
        ("letter", QPageSize.PageSizeId.Letter),
        ("a4", QPageSize.PageSizeId.A4),
        ("legal", QPageSize.PageSizeId.Legal),
        ("junk", QPageSize.PageSizeId.Letter),
    ],
)
def test_page_layout_uses_expected_page_size_id(
    qapp, key: str, expected_id: QPageSize.PageSizeId
):
    """``_page_layout`` returns a layout with the matching PageSizeId."""
    from epy_reports._ui.tab import MarkdownTab

    layout = MarkdownTab._page_layout(key)
    assert layout.pageSize().id() == expected_id
