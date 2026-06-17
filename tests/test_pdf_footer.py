"""Tests for the PDF footer stamping helper."""

from __future__ import annotations

import pytest

pypdf = pytest.importorskip("pypdf")
reportlab = pytest.importorskip("reportlab")

from epy_mdr._pdf_footer import add_footer  # noqa: E402


def _make_pdf(path, pages: int = 1) -> None:
    """Create a tiny multi-page PDF with reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=A4)
    for i in range(pages):
        pdf.drawString(72, 720, f"Body page {i + 1}")
        pdf.showPage()
    pdf.save()


def test_add_footer_preserves_page_count(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    _make_pdf(pdf_path, pages=3)
    add_footer(
        pdf_path, "ANM Ingeniería", page_numbers=True, lang="es"
    )
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == 3


def test_add_footer_no_settings_is_noop(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    _make_pdf(pdf_path, pages=1)
    before = pdf_path.read_bytes()
    add_footer(pdf_path, "", page_numbers=False)
    assert pdf_path.read_bytes() == before


def test_add_footer_text_only(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    _make_pdf(pdf_path, pages=2)
    add_footer(pdf_path, "Confidential", page_numbers=False)
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == 2
