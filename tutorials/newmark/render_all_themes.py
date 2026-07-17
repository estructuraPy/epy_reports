"""Render ``newmark.md`` once per epy_reports theme to HTML + PDF.

Demonstrates the full epy_reports publishing pipeline on a feature-complete
document: YAML front matter with cover page, TOC/LOF/LOT/LOE index markers,
page breaks, footnotes, IEEE bibliography, Quarto cross-references
(``@sec-``/``@fig-``/``@eq-``), titled callouts, figures, tables and
display equations.  Each theme is rendered with its own ``:root { … }`` block
(``Theme.to_css()``), then printed to PDF via Qt WebEngine after MathJax
finishes typesetting.

The export pipeline uses two passes to inject accurate page numbers into the
index blocks (TOC, LOF, LOT, LOE):

1. **Pass 1** — render with ``paged=False`` (print-ready layout), export to a
   temporary PDF, then extract the anchor→page-number mapping from the PDF's
   named destinations using :mod:`pypdf`.
2. **Pass 2** — inject the page numbers into the HTML, reload, and export the
   final PDF.

After the final PDF is written, the ``footer`` and ``page-numbers`` front-matter
values are applied as a :mod:`reportlab` overlay via
:func:`epy_reports._pdf_footer.add_footer`, and the ``header`` cells (if present)
via :func:`epy_reports._pdf_footer.add_header`.

Run it from this directory::

    python render_all_themes.py

Output lands in ``_render/themes/`` (git-ignored).

Typography note
---------------
The PDFs use the fonts each theme requests **only when those font families
are installed on the machine doing the render**.  On a PC missing a given
family, Qt/Pandoc fall back to the nearest available font, so the same
document may look slightly different across machines.  Layout, colors,
spacing and structure are theme-defined and stable; only the glyph shapes
depend on locally available fonts.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QMarginsF, Qt, QTimer, QUrl
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent

# Prefer an installed epy_reports; fall back to the in-repo source tree so the
# example runs straight from a clone without `pip install -e .`.
try:
    from epy_reports import themes
    from epy_reports._design import document_css
    from epy_reports._pdf_footer import (
        add_footer,
        add_header,
        add_page_background,
        add_watermark,
        extract_anchor_pages,
    )
    from epy_reports.renderer import (
        inject_page_numbers,
        normalize_page_size,
        render_markdown,
    )
    from epy_reports.snippets import parse_front_matter, parse_header_cells
except ImportError:
    sys.path.insert(0, str(ROOT.parent.parent / "src"))
    from epy_reports import themes
    from epy_reports._design import document_css
    from epy_reports._pdf_footer import (
        add_footer,
        add_header,
        add_page_background,
        add_watermark,
        extract_anchor_pages,
    )
    from epy_reports.renderer import (
        inject_page_numbers,
        normalize_page_size,
        render_markdown,
    )
    from epy_reports.snippets import parse_front_matter, parse_header_cells

SOURCE = ROOT / "newmark.md"
OUT_DIR = ROOT / "_render" / "themes"

# (output suffix, source file) — the base .md is English, _es is Spanish; the
# example ships both languages and every theme is rendered in each one.
LANGS = [("", SOURCE), ("_es", ROOT / "newmark_es.md")]

WAIT_FOR_MATHJAX_JS = r"""
(function () {
    window._mathjax_done = false;
    function arm() {
        if (window.MathJax && MathJax.startup && MathJax.startup.promise) {
            MathJax.startup.promise.then(function () {
                window._mathjax_done = true;
            });
            return true;
        }
        return false;
    }
    if (arm()) return;
    var iv = setInterval(function () {
        if (arm()) clearInterval(iv);
    }, 100);
})();
"""

_PAGE_SIZE_IDS = {
    "letter": QPageSize.PageSizeId.Letter,
    "a4": QPageSize.PageSizeId.A4,
    "legal": QPageSize.PageSizeId.Legal,
}


def _page_layout(page_size: str) -> QPageLayout:
    size_id = _PAGE_SIZE_IDS.get(normalize_page_size(page_size), _PAGE_SIZE_IDS["letter"])
    # Zero printer margin: Paged.js already lays out every page with a
    # 30 mm @page margin, so the printed page maps 1:1 onto the sheet. The
    # theme background is painted edge to edge afterwards by
    # add_page_background; the 15 mm footer/header overlays sit inside the
    # 30 mm margin with clearance.
    return QPageLayout(
        QPageSize(size_id),
        QPageLayout.Orientation.Portrait,
        QMarginsF(0.0, 0.0, 0.0, 0.0),
        QPageLayout.Unit.Millimeter,
    )


def _section_segments(anchors: dict) -> list[tuple[int, str]] | None:
    """Extract ``(page, style)`` section boundaries from PDF anchors."""
    found: list[tuple[int, str]] = []
    for anchor_id, page in anchors.items():
        if anchor_id.startswith("epy-section-roman-"):
            found.append((page, "roman"))
        elif anchor_id.startswith("epy-section-arabic-"):
            found.append((page, "arabic"))
    return sorted(found) or None


class ThemeExporter:
    """Render one theme: two-pass HTML→PDF with page number injection."""

    MAX_WAIT_MS = 60_000  # Paged.js pagination of a long doc can be slow
    POLL_MS = 300

    def __init__(
        self, theme_id: str, source: str, meta: dict, suffix: str, on_done
    ) -> None:
        self.theme_id = theme_id
        self.source = source
        self.meta = meta
        self.suffix = suffix
        self.on_done = on_done

        self.html_path = OUT_DIR / f"newmark_{theme_id}{suffix}.html"
        self.pdf_path = OUT_DIR / f"newmark_{theme_id}{suffix}.pdf"
        self._pass1_pdf = OUT_DIR / f"_p1_{theme_id}{suffix}.pdf"
        self._tmp_html = ROOT / f"_tmp_{theme_id}{suffix}.html"

        self._elapsed_ms = 0
        self._pending_pdf: Path | None = None
        self._pending_after = None
        self._page_bg = ""
        # First physical page holding real content (after cover + indexes);
        # overlays start here and the footer renumbers content from 1.
        self._first_content_page = 1
        # Section-break boundaries (Roman/Arabic), if the document has any.
        self._segments: list[tuple[int, str]] | None = None

        self.view = QWebEngineView()
        # Paged.js measures content with getBoundingClientRect, which only
        # works once the view is laid out. WA_DontShowOnScreen lays it out
        # offscreen (no visible window) so pagination works headlessly.
        self.view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.view.resize(900, 1200)
        self.view.show()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def go(self) -> None:
        lang = self.suffix or " (en)"
        print(f"\n=== theme: {self.theme_id}{lang} ===")
        theme = themes.get(self.theme_id)
        self._page_bg = theme.css_vars.get("bg", "")
        page_size = normalize_page_size(self.meta.get("page-size"))
        # document_css() (not the bare theme.to_css()) also carries the
        # design-component CSS (disclosure, verdict, checklist, badges,
        # ...) this example exercises — a plain theme stylesheet leaves
        # them unstyled.
        html = render_markdown(
            self.source,
            base_dir=ROOT,
            theme_css=document_css(theme),
            paged=False,
            page_size=page_size,
            for_export=True,
        )
        self.html_path.write_text(html, encoding="utf-8")
        self._pass1_html = html
        print(f"  HTML  -> {self.html_path.name}  ({len(html):,} chars)")
        self._load_and_print(html, self._pass1_pdf, self._after_pass1)

    # ------------------------------------------------------------------
    # Shared async printing machinery
    # ------------------------------------------------------------------

    def _load_and_print(self, html: str, pdf_path: Path, after_print) -> None:
        self._pending_pdf = pdf_path
        self._pending_after = after_print
        self._elapsed_ms = 0
        self._tmp_html.write_text(html, encoding="utf-8")
        self.view.loadFinished.connect(
            self._on_load, Qt.ConnectionType.SingleShotConnection
        )
        self.view.load(QUrl.fromLocalFile(str(self._tmp_html.resolve())))

    def _on_load(self, ok: bool) -> None:
        if not ok:
            print(f"  [{self.theme_id}] load failed")
            if self._pending_after:
                self._pending_after(False)
            return
        self.view.page().runJavaScript(WAIT_FOR_MATHJAX_JS)
        QTimer.singleShot(self.POLL_MS, self._poll)

    def _poll(self) -> None:
        self._elapsed_ms += self.POLL_MS
        # The Paged.js runner sets _paged_done only after MathJax has
        # finished and pagination (incl. footnote placement) is complete.
        self.view.page().runJavaScript(
            "window._paged_done === true", self._on_poll_result
        )

    def _on_poll_result(self, done: bool) -> None:
        if done or self._elapsed_ms >= self.MAX_WAIT_MS:
            if not done:
                print(f"  [{self.theme_id}] Paged.js timeout — printing anyway")
            else:
                print(f"  [{self.theme_id}] Paged.js ready after {self._elapsed_ms} ms")
            QTimer.singleShot(self.POLL_MS, self._do_print)
        else:
            QTimer.singleShot(self.POLL_MS, self._poll)

    def _do_print(self) -> None:
        self.view.page().pdfPrintingFinished.connect(
            self._on_printed, Qt.ConnectionType.SingleShotConnection
        )
        self.view.page().printToPdf(
            str(self._pending_pdf),
            _page_layout(self.meta.get("page-size", "letter")),
        )

    def _on_printed(self, _path: str, ok: bool) -> None:
        size = self._pending_pdf.stat().st_size if self._pending_pdf.exists() else 0
        label = "pass1" if self._pending_pdf == self._pass1_pdf else "pass2"
        print(f"  PDF ({label}) -> {self._pending_pdf.name}  ok={ok}  ({size:,} bytes)")
        if self._pending_after:
            self._pending_after(ok)

    # ------------------------------------------------------------------
    # Two-pass logic
    # ------------------------------------------------------------------

    def _after_pass1(self, ok: bool) -> None:
        if not ok:
            self._finish()
            return

        anchor_to_page = extract_anchor_pages(self._pass1_pdf)
        self._segments = _section_segments(anchor_to_page)
        # Section markers are page breaks, not body content; exclude them
        # when locating the first content page.
        content_anchors = {
            a: p for a, p in anchor_to_page.items()
            if not a.startswith("epy-section-")
        }
        if content_anchors:
            # All named destinations live in the body (index blocks emit
            # only links), so the smallest one is the first content page.
            # Everything before it (cover + TOC/LOF/LOT/LOE) is unnumbered
            # front matter; content page numbers restart at 1 from there.
            self._first_content_page = min(content_anchors.values())
            offset = self._first_content_page - 1
            print(
                f"  [{self.theme_id}] extracted {len(anchor_to_page)} anchors "
                f"— content starts on physical page {self._first_content_page} "
                f"— running pass 2"
            )
            html2 = inject_page_numbers(self._pass1_html, anchor_to_page, offset)
            # Update saved HTML with page numbers
            self.html_path.write_text(html2, encoding="utf-8")
            self._load_and_print(html2, self.pdf_path, self._after_pass2)
        else:
            print(f"  [{self.theme_id}] no named destinations — skipping pass 2")
            import shutil
            shutil.copy(self._pass1_pdf, self.pdf_path)
            self._apply_overlays_and_finish(ok=True)

    def _after_pass2(self, ok: bool) -> None:
        self._apply_overlays_and_finish(ok)

    def _apply_overlays_and_finish(self, ok: bool) -> None:
        if ok and self.pdf_path.exists():
            # Paint the theme page background edge to edge on every page
            # first (the printer margin is left white by Qt); the footer
            # and header overlays are then stamped on top.
            if self._page_bg:
                add_page_background(self.pdf_path, self._page_bg)
                print(f"  [{self.theme_id}] page background {self._page_bg}")
            header_cells = parse_header_cells(self.meta.get("header"))
            footer_text = str(self.meta.get("footer", "") or "")
            page_numbers_flag = str(self.meta.get("page-numbers", "")).lower() in (
                "true", "yes", "1",
            )
            lang = str(self.meta.get("lang", "en"))
            # Start overlays on the first content page (after cover + index
            # front matter). Falls back to skipping just the cover when no
            # destinations were found (pass 2 skipped).
            has_cover = str(self.meta.get("cover", "")).lower() in ("true", "yes", "1")
            overlay_start = max(self._first_content_page, 2 if has_cover else 1)
            watermark = str(self.meta.get("watermark", "") or "").strip()
            try:
                if watermark and (ROOT / watermark).is_file():
                    add_watermark(self.pdf_path, ROOT / watermark)
                    print(f"  [{self.theme_id}] watermark {watermark}")
                if any(header_cells):
                    add_header(
                        self.pdf_path, header_cells,
                        lang=lang, start_page=overlay_start,
                    )
                    print(f"  [{self.theme_id}] header stamped (from page {overlay_start})")
                if footer_text or page_numbers_flag:
                    add_footer(
                        self.pdf_path,
                        footer_text,
                        page_numbers=page_numbers_flag,
                        lang=lang,
                        start_page=overlay_start,
                        segments=self._segments,
                    )
                    label = (
                        "sectioned" if self._segments
                        else f"from page {overlay_start}"
                    )
                    print(f"  [{self.theme_id}] footer stamped ({label})")
            except RuntimeError as exc:
                print(f"  [{self.theme_id}] overlay error: {exc}")
        self._finish()

    def _finish(self) -> None:
        try:
            self._pass1_pdf.unlink(missing_ok=True)
        except OSError:
            pass
        try:
            self._tmp_html.unlink(missing_ok=True)
        except OSError:
            pass
        self.on_done()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    theme_ids = [only] if only else list(themes.THEMES.keys())

    # Flat queue of (theme_id, source_text, meta, suffix) over both languages.
    jobs: list[tuple] = []
    for suffix, src in LANGS:
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8")
        meta = parse_front_matter(text)
        for theme_id in theme_ids:
            jobs.append((theme_id, text, meta, suffix))

    def kick_next() -> None:
        if not jobs:
            print("\nAll themes rendered.")
            app.quit()
            return
        theme_id, text, meta, suffix = jobs.pop(0)
        exporter = ThemeExporter(theme_id, text, meta, suffix, on_done=kick_next)
        main._current = exporter  # type: ignore[attr-defined]
        exporter.go()

    QTimer.singleShot(0, kick_next)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
