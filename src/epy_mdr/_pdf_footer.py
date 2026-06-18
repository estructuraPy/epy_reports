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

import contextlib
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


def extract_anchor_pages(pdf_path: Path) -> dict[str, int]:
    """Return ``anchor id → 1-based page`` from a Qt-generated PDF.

    Qt WebEngine records HTML element ids as PDF named destinations, so a
    first export pass yields the physical page of every anchored heading,
    figure, table and equation. The index blocks emit only links (no
    destinations), so every entry here points into the document body —
    ``min(result.values())`` is therefore the first content page.

    Returns an empty dict when :mod:`pypdf` is missing or the PDF has no
    named destinations (older Qt), so the caller can skip the second pass
    gracefully.
    """
    try:
        from pypdf import PdfReader  # noqa: PLC0415
    except ImportError:  # pragma: no cover - env guard
        return {}
    try:
        reader = PdfReader(str(pdf_path))
        result: dict[str, int] = {}
        for name, dest in reader.named_destinations.items():
            with contextlib.suppress(Exception):  # skip unresolvable dests
                result[name.lstrip("/")] = (
                    reader.get_destination_page_number(dest) + 1
                )
        return result
    except Exception:  # noqa: BLE001 - corrupt/unreadable PDF
        return {}


def add_page_background(
    pdf_path: Path,
    color: str,
    *,
    start_page: int = 1,
) -> None:
    """Paint a solid full-sheet background behind every page, in place.

    Qt WebEngine lays out the body inside the printer margin, so the margin
    band of every page is left unpainted (white) even for colored themes —
    Chromium never paints the printer-margin area. This draws a ``color``
    rectangle covering the whole media box *below* the existing page
    content, so the theme background reaches the paper edges without
    touching the already-laid-out body, footnotes or overlays. The page
    keeps its links because the backdrop is merged under it (``over=False``).

    Args:
        pdf_path: Path to an existing PDF; overwritten with the result.
        color: CSS hex color (``#RRGGBB``) of the theme page background.
            An empty or unparseable value leaves the PDF untouched.
        start_page: First 1-based page to paint (defaults to every page,
            cover and index pages included).

    Raises:
        RuntimeError: When :mod:`pypdf` or :mod:`reportlab` is not installed.
    """
    if not color:
        return
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from reportlab.lib.colors import HexColor  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env guard
        raise RuntimeError(
            "PDF backgrounds require the 'pypdf' and 'reportlab' packages. "
            "Install them with: pip install pypdf reportlab"
        ) from exc

    try:
        fill = HexColor(color)
    except (ValueError, TypeError):
        return  # unparseable color → leave the PDF as-is

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages, start=1):
        if index >= start_page:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            buffer = io.BytesIO()
            backdrop_canvas = canvas.Canvas(buffer, pagesize=(width, height))
            backdrop_canvas.setFillColor(fill)
            backdrop_canvas.rect(0, 0, width, height, fill=1, stroke=0)
            backdrop_canvas.showPage()
            backdrop_canvas.save()
            buffer.seek(0)
            backdrop = PdfReader(buffer).pages[0]
            # over=False → backdrop goes underneath, page content (and its
            # link annotations) stay on top.
            page.merge_page(backdrop, over=False)
        writer.add_page(page)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


def add_footer(
    pdf_path: Path,
    footer_text: str,
    *,
    page_numbers: bool,
    lang: str = "en",
    start_page: int = 1,
) -> None:
    """Stamp pages of ``pdf_path`` with a footer, in place.

    Draws ``footer_text`` at the bottom-left and, when ``page_numbers`` is
    ``True``, a localized "Page X of Y" string at the bottom-right.

    Args:
        pdf_path: Path to an existing PDF; overwritten with the stamped
            version.
        footer_text: Static text drawn at the bottom-left.  May be empty.
        page_numbers: When ``True``, draw "Page X of Y" at bottom-right.
        lang: Two-letter language tag selecting the page-number wording.
        start_page: First 1-based physical page to stamp.  Pages before
            this (cover and index pages — TOC / LOF / LOT / LOE) are
            passed through unchanged and carry no footer or page number.
            Page numbering restarts at 1 on ``start_page`` and the
            "of Y" total counts only the stamped (content) pages, so the
            front matter is effectively unnumbered.

    Raises:
        RuntimeError: When :mod:`pypdf` or :mod:`reportlab` is not installed.
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
    # Page numbers restart at 1 on the first stamped (content) page and the
    # "of Y" total counts only those pages, so cover + index front matter
    # stays unnumbered instead of forcing the body to start at "Page N".
    content_total = max(total - start_page + 1, 0)
    margin = _MARGIN_MM * _MM_TO_PT

    for index, page in enumerate(reader.pages, start=1):
        if index >= start_page:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=(width, height))
            pdf.setFont(_FONT_NAME, _FONT_SIZE)
            pdf.setFillGray(_GRAY)
            if footer_text:
                pdf.drawString(margin, margin, footer_text)
            if page_numbers:
                current = index - start_page + 1
                label = _page_label(lang, current, content_total)
                pdf.drawRightString(width - margin, margin, label)
            pdf.showPage()
            pdf.save()
            buffer.seek(0)
            overlay = PdfReader(buffer).pages[0]
            page.merge_page(overlay)
        writer.add_page(page)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


# Header geometry
_HEADER_ROW_H_PT = 12.0  # height of each row in points (~4.2 mm)
_HEADER_COLS = 3
_STROKE_GRAY = 0.70


def add_header(
    pdf_path: Path,
    cells: list[str],
    *,
    lang: str = "en",  # noqa: ARG001 — reserved for future l10n
    start_page: int = 1,
) -> None:
    """Stamp a 2-row × 3-column grid header onto pages of ``pdf_path``.

    Up to 6 strings may be provided.  Cells are filled in row-major order::

        [cells[0]]  [cells[1]]  [cells[2]]   ← row 1
        [cells[3]]  [cells[4]]  [cells[5]]   ← row 2

    If only 3 values are given, a single-row header is drawn.  Columns are
    left-, center-, and right-aligned respectively.  The grid is placed in
    the top page margin (≈15 mm from the paper edge) so it never overlaps
    the document body.

    Args:
        pdf_path: Path to an existing PDF; overwritten with the stamped
            version.
        cells: Up to 6 strings for the header grid.  Missing cells default to
            empty strings.
        lang: Two-letter language tag (reserved; not used currently).
        start_page: First 1-based page number to stamp.  Pages before this
            (e.g. a cover page) are passed through unchanged.

    Raises:
        RuntimeError: When :mod:`pypdf` or :mod:`reportlab` is not installed.
    """
    cells = list(cells or [])
    if not any(cells):
        return

    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from reportlab.pdfgen import canvas as rl_canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PDF headers require the 'pypdf' and 'reportlab' packages. "
            "Install them with: pip install pypdf reportlab"
        ) from exc

    # Pad / truncate to exactly 6 cells
    cells = (cells + [""] * 6)[:6]
    has_row2 = any(cells[3:])
    n_rows = 2 if has_row2 else 1

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    margin = _MARGIN_MM * _MM_TO_PT
    row_h = _HEADER_ROW_H_PT

    for page_index, page in enumerate(reader.pages, start=1):
        if page_index < start_page:
            writer.add_page(page)
            continue
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        buffer = io.BytesIO()
        c = rl_canvas.Canvas(buffer, pagesize=(width, height))
        c.setFont(_FONT_NAME, _FONT_SIZE)

        grid_x = margin
        grid_w = width - 2 * margin
        col_w = grid_w / _HEADER_COLS
        grid_top = height - margin          # top edge of grid (near paper top)
        grid_h = n_rows * row_h
        grid_bot = grid_top - grid_h

        # Border
        c.setStrokeGray(_STROKE_GRAY)
        c.setLineWidth(0.5)
        c.rect(grid_x, grid_bot, grid_w, grid_h, fill=0, stroke=1)

        # Column dividers
        for col in range(1, _HEADER_COLS):
            x = grid_x + col * col_w
            c.line(x, grid_bot, x, grid_top)

        # Row divider (only when 2 rows)
        if n_rows == 2:
            mid_y = grid_bot + row_h
            c.line(grid_x, mid_y, grid_x + grid_w, mid_y)

        # Cell text
        c.setFillGray(_GRAY)
        for i, text in enumerate(cells[: n_rows * _HEADER_COLS]):
            if not text:
                continue
            row = i // _HEADER_COLS
            col = i % _HEADER_COLS
            y_top = grid_top - row * row_h
            y_base = y_top - row_h / 2 - _FONT_SIZE / 4
            x_left = grid_x + col * col_w
            pad = 3  # inner horizontal padding in points
            if col == 0:
                c.drawString(x_left + pad, y_base, text)
            elif col == 1:
                c.drawCentredString(x_left + col_w / 2, y_base, text)
            else:
                c.drawRightString(x_left + col_w - pad, y_base, text)

        c.showPage()
        c.save()
        buffer.seek(0)
        overlay = PdfReader(buffer).pages[0]
        page.merge_page(overlay)
        writer.add_page(page)

    with pdf_path.open("wb") as handle:
        writer.write(handle)
