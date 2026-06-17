"""Stamp a static footer and page numbers onto an existing PDF.

The PDF is rewritten in place: every page gets an overlay canvas
(drawn with :mod:`reportlab`) merged on top of it (via :mod:`pypdf`).
Both libraries are permissively licensed (BSD), so they are compatible
with epy_mdr's MIT license. PyMuPDF/fitz is deliberately avoided
because of its AGPL licensing.

The heavy dependencies are imported lazily inside :func:`add_footer`,
so this module imports cleanly even when they are missing; a clear
:class:`RuntimeError` is raised only when the function is actually
called without them installed.
"""

from __future__ import annotations

import io
from pathlib import Path

# Footer geometry / styling.
_MARGIN_MM = 15.0
_MM_TO_PT = 72.0 / 25.4
_FONT_NAME = "Helvetica"
_FONT_SIZE = 8.0
_GRAY = 0.45  # muted gray (0 = black, 1 = white)

# Localized "Page X of Y" templates.
_PAGE_LABELS: dict[str, str] = {
    "en": "Page {current} of {total}",
    "es": "Pág. {current} de {total}",
}


def _page_label(lang: str, current: int, total: int) -> str:
    """Return the localized page-number string for one page."""
    key = lang[:2].lower() if lang else "en"
    template = _PAGE_LABELS.get(key, _PAGE_LABELS["en"])
    return template.format(current=current, total=total)


def add_footer(
    pdf_path: Path,
    footer_text: str,
    *,
    page_numbers: bool,
    lang: str = "en",
) -> None:
    """Stamp every page of ``pdf_path`` with a footer, in place.

    Draws ``footer_text`` at the bottom-left of every page and, when
    ``page_numbers`` is ``True``, a localized "Page X of Y" string at
    the bottom-right. The font is small and muted gray, with ~15 mm
    margins. Page sizes are read per page so mixed-size documents keep
    their layout.

    Args:
        pdf_path: Path to an existing PDF; overwritten with the stamped
            version.
        footer_text: Static text drawn at the bottom-left. May be empty.
        page_numbers: When ``True``, draw "Page X of Y" at bottom-right.
        lang: Two-letter language tag selecting the page-number wording.

    Raises:
        RuntimeError: When :mod:`pypdf` or :mod:`reportlab` is not
            installed.
    """
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env guard
        raise RuntimeError(
            "PDF footers require the 'pypdf' and 'reportlab' packages. "
            "Install them with: pip install pypdf reportlab"
        ) from exc

    if not footer_text and not page_numbers:
        return  # nothing to stamp

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    total = len(reader.pages)
    margin = _MARGIN_MM * _MM_TO_PT

    for index, page in enumerate(reader.pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=(width, height))
        pdf.setFont(_FONT_NAME, _FONT_SIZE)
        pdf.setFillGray(_GRAY)
        if footer_text:
            pdf.drawString(margin, margin, footer_text)
        if page_numbers:
            label = _page_label(lang, index, total)
            pdf.drawRightString(width - margin, margin, label)
        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        overlay = PdfReader(buffer).pages[0]
        page.merge_page(overlay)
        writer.add_page(page)

    with pdf_path.open("wb") as handle:
        writer.write(handle)
