"""Tests for the PDF footer/header/background/watermark internals.

reportlab, pypdf and Pillow are declared project dependencies, so they are
imported directly here (the public ``add_*`` functions raise a clear
RuntimeError only when they are genuinely absent — not the case in this
environment).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from epy_reports import _pdf_footer
from epy_reports._pdf_footer import (
    _page_label,
    _page_stamp,
    _roman,
    add_footer,
    add_header,
    add_page_background,
    add_watermark,
    extract_anchor_pages,
)


def _make_pdf(path: Path, pages: int = 1) -> None:
    """Create a tiny multi-page PDF with reportlab."""
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for i in range(pages):
        pdf.drawString(72, 720, f"Body page {i + 1}")
        pdf.showPage()
    pdf.save()


def _make_png(path: Path) -> None:
    """Write a minimal 2x2 RGBA PNG for watermark tests."""
    width = height = 2
    raw = b""
    for _ in range(height):
        raw += b"\x00"  # filter byte per scanline
        raw += b"\xff\x00\x00\xff" * width  # RGBA red pixels
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(png)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_page_label_english():
    assert _page_label("en", 2, 5) == "Page 2 of 5"


def test_page_label_spanish():
    assert _page_label("es", 1, 3) == "Pág. 1 de 3"


def test_page_label_unknown_lang_falls_back_to_english():
    assert _page_label("zz", 1, 1) == "Page 1 of 1"


def test_roman_basic():
    assert _roman(1) == "i"
    assert _roman(4) == "iv"
    assert _roman(9) == "ix"
    assert _roman(2024) == "mmxxiv"


def test_roman_non_positive_returns_str():
    assert _roman(0) == "0"
    assert _roman(-3) == "-3"


# ---------------------------------------------------------------------------
# _page_stamp
# ---------------------------------------------------------------------------


def test_page_stamp_front_matter_not_numbered():
    """Pages before start_page are not stamped."""
    stamp, label = _page_stamp(
        1, start_page=3, content_total=2, lang="en",
        segments=None, page_numbers=True,
    )
    assert stamp is False
    assert label is None


def test_page_stamp_content_page_numbered():
    """A content page gets a 'Page X of Y' label."""
    stamp, label = _page_stamp(
        3, start_page=3, content_total=2, lang="en",
        segments=None, page_numbers=True,
    )
    assert stamp is True
    assert label == "Page 1 of 2"


def test_page_stamp_no_page_numbers_returns_no_label():
    """With numbering off, a content page stamps text but no label."""
    stamp, label = _page_stamp(
        3, start_page=3, content_total=2, lang="en",
        segments=None, page_numbers=False,
    )
    assert stamp is True
    assert label is None


def test_page_stamp_segments_roman_then_arabic():
    """Segmented numbering restarts per section in its own style."""
    segments = [(1, "roman"), (3, "arabic")]
    # Page 2 is in the roman segment, second page → "ii".
    _, roman_label = _page_stamp(
        2, start_page=1, content_total=0, lang="en",
        segments=segments, page_numbers=True,
    )
    assert roman_label == "ii"
    # Page 3 starts the arabic segment → "1".
    _, arabic_label = _page_stamp(
        3, start_page=1, content_total=0, lang="en",
        segments=segments, page_numbers=True,
    )
    assert arabic_label == "1"


def test_page_stamp_segments_before_first_boundary():
    """A page before the first segment boundary is unnumbered."""
    segments = [(2, "arabic")]
    stamp, label = _page_stamp(
        1, start_page=1, content_total=0, lang="en",
        segments=segments, page_numbers=True,
    )
    assert stamp is False
    assert label is None


# ---------------------------------------------------------------------------
# Footer with segments (integration)
# ---------------------------------------------------------------------------


def test_add_footer_with_segments_preserves_pages(tmp_path):
    pdf_path = tmp_path / "seg.pdf"
    _make_pdf(pdf_path, pages=4)
    add_footer(
        pdf_path, "Footer", page_numbers=True,
        segments=[(1, "roman"), (3, "arabic")],
    )
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf_path)).pages) == 4


# ---------------------------------------------------------------------------
# add_header
# ---------------------------------------------------------------------------


def test_add_header_preserves_page_count(tmp_path):
    pdf_path = tmp_path / "hdr.pdf"
    _make_pdf(pdf_path, pages=2)
    add_header(pdf_path, ["Left", "Center", "Right"])
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf_path)).pages) == 2


def test_add_header_two_rows(tmp_path):
    pdf_path = tmp_path / "hdr2.pdf"
    _make_pdf(pdf_path, pages=1)
    add_header(
        pdf_path, ["TL", "TC", "TR", "BL", "BC", "BR"], start_page=1
    )
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf_path)).pages) == 1


# ---------------------------------------------------------------------------
# add_page_background
# ---------------------------------------------------------------------------


def test_add_page_background_preserves_pages(tmp_path):
    pdf_path = tmp_path / "bg.pdf"
    _make_pdf(pdf_path, pages=2)
    add_page_background(pdf_path, "#EEEEEE")
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf_path)).pages) == 2


def test_add_page_background_empty_color_is_noop(tmp_path):
    pdf_path = tmp_path / "bg2.pdf"
    _make_pdf(pdf_path, pages=1)
    before = pdf_path.read_bytes()
    add_page_background(pdf_path, "")
    assert pdf_path.read_bytes() == before


def test_add_page_background_bad_color_is_noop(tmp_path):
    pdf_path = tmp_path / "bg3.pdf"
    _make_pdf(pdf_path, pages=1)
    before = pdf_path.read_bytes()
    add_page_background(pdf_path, "not-a-color")
    assert pdf_path.read_bytes() == before


# ---------------------------------------------------------------------------
# add_watermark
# ---------------------------------------------------------------------------


def test_add_watermark_preserves_pages(tmp_path):
    pdf_path = tmp_path / "wm.pdf"
    _make_pdf(pdf_path, pages=2)
    img = tmp_path / "logo.png"
    _make_png(img)
    add_watermark(pdf_path, img)
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf_path)).pages) == 2


def test_add_watermark_missing_image_is_noop(tmp_path):
    pdf_path = tmp_path / "wm2.pdf"
    _make_pdf(pdf_path, pages=1)
    before = pdf_path.read_bytes()
    add_watermark(pdf_path, tmp_path / "no-such-image.png")
    assert pdf_path.read_bytes() == before


# ---------------------------------------------------------------------------
# extract_anchor_pages
# ---------------------------------------------------------------------------


def test_extract_anchor_pages_no_destinations(tmp_path):
    """A plain PDF with no named destinations yields an empty map."""
    pdf_path = tmp_path / "plain.pdf"
    _make_pdf(pdf_path, pages=1)
    assert extract_anchor_pages(pdf_path) == {}


def test_extract_anchor_pages_corrupt_returns_empty(tmp_path):
    """A corrupt PDF is handled gracefully, not crashing the export."""
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 totally broken")
    assert extract_anchor_pages(bad) == {}


def test_constants_are_sane():
    """The module geometry constants keep their documented values."""
    assert _pdf_footer._FONT_NAME == "Helvetica"
    assert _pdf_footer._HEADER_COLS == 3
