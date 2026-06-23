"""Headless Markdown -> PDF rendering for the scriptable API.

Single-pass Paged.js print flow (theme page background, header/footer, page
numbers from 1, grayscale watermark and document metadata stamped in) so
``Report.to_pdf`` works without the GUI. The interactive editor keeps the
richer two-pass flow (cover-aware numbering, section restarts). Requires
PySide6; the Qt import is deferred to call time.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

_PAGE_SIZES = {"letter": "Letter", "a4": "A4", "legal": "Legal"}


def render_report_pdf(
    source: str,
    out_path: Path,
    *,
    base_dir: Path | None,
    theme_css: str,
    page_bg: str = "",
    timeout_ms: int = 60000,
) -> None:
    """Render Markdown ``source`` to a paginated PDF via Paged.js."""
    from PySide6.QtCore import (  # noqa: PLC0415
        QElapsedTimer,
        QEventLoop,
        QMarginsF,
        Qt,
        QUrl,
    )
    from PySide6.QtGui import QPageLayout, QPageSize  # noqa: PLC0415
    from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: PLC0415
    from PySide6.QtWidgets import QApplication  # noqa: PLC0415

    from epy_reports import _pdf_footer  # noqa: PLC0415
    from epy_reports.renderer import (  # noqa: PLC0415, E501
        normalize_page_size,
        render_markdown,
    )
    from epy_reports.snippets import (  # noqa: PLC0415
        parse_front_matter,
        parse_header_cells,
    )
    from epy_reports.template import is_truthy  # noqa: PLC0415

    meta = parse_front_matter(source)
    page_size = normalize_page_size(meta.get("page-size"))
    lang = meta.get("lang", "en")

    app = QApplication.instance() or QApplication([])
    html = render_markdown(
        source, base_dir=base_dir, theme_css=theme_css,
        page_size=page_size, for_export=True,
    )
    tmp = out_path.with_suffix(".tmp.html")
    tmp.write_text(html, encoding="utf-8")

    view = QWebEngineView()
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    view.resize(820, 1060)
    view.show()

    page_enum = getattr(
        QPageSize.PageSizeId, _PAGE_SIZES.get(page_size, "Letter")
    )
    layout = QPageLayout(
        QPageSize(page_enum), QPageLayout.Orientation.Portrait,
        QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter,
    )

    state = {"printed": False, "ok": False}

    def pump(ms: int) -> None:
        timer = QElapsedTimer()
        timer.start()
        while timer.elapsed() < ms:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)

    def js(expr: str) -> object:
        box: dict[str, object] = {"v": None}
        view.page().runJavaScript(expr, lambda v: box.__setitem__("v", v))
        timer = QElapsedTimer()
        timer.start()
        while box["v"] is None and timer.elapsed() < 4000:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
        return box["v"]

    try:
        loaded = {"ok": False}
        view.loadFinished.connect(lambda ok: loaded.__setitem__("ok", ok))
        view.load(QUrl.fromLocalFile(str(tmp.resolve())))
        timer = QElapsedTimer()
        timer.start()
        while not loaded["ok"] and timer.elapsed() < timeout_ms:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
        while js("window._paged_done === true") is not True and (
            timer.elapsed() < timeout_ms
        ):
            pump(150)
        pump(200)

        def on_printed(_p: str, ok: bool) -> None:
            state["ok"] = ok
            state["printed"] = True

        view.page().pdfPrintingFinished.connect(on_printed)
        view.page().printToPdf(str(out_path), layout)
        while not state["printed"] and timer.elapsed() < timeout_ms + 10000:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
    finally:
        view.deleteLater()
        pump(20)
        tmp.unlink(missing_ok=True)

    if not (state["ok"] and out_path.exists()):
        raise RuntimeError("PDF export failed (Paged.js did not complete)")

    # Stamp overlays (best-effort) on a temp copy, then move into place.
    work = Path(tempfile.mkdtemp(prefix="epy_reports_pdf_")) / "out.pdf"
    work.write_bytes(out_path.read_bytes())
    try:
        if page_bg:
            _pdf_footer.add_page_background(work, page_bg)
        watermark = (meta.get("watermark") or "").strip()
        if watermark:
            wm = Path(watermark)
            if not wm.is_absolute() and base_dir is not None:
                wm = base_dir / watermark
            if wm.is_file():
                _pdf_footer.add_watermark(work, wm)
        header_cells = parse_header_cells(meta.get("header"))
        if any(header_cells):
            _pdf_footer.add_header(work, header_cells, lang=lang, start_page=1)
        footer_text = meta.get("footer", "")
        page_numbers = is_truthy(meta.get("page-numbers"))
        if footer_text or page_numbers:
            _pdf_footer.add_footer(
                work, footer_text, page_numbers=page_numbers,
                lang=lang, start_page=1,
            )
        _pdf_footer.add_metadata(
            work,
            title=meta.get("title", ""),
            author=meta.get("author", ""),
            subject=meta.get("subtitle", ""),
            keywords=meta.get("keywords", ""),
            rights=meta.get("copyright", ""),
        )
        out_path.write_bytes(work.read_bytes())
    finally:
        import shutil  # noqa: PLC0415

        shutil.rmtree(work.parent, ignore_errors=True)
