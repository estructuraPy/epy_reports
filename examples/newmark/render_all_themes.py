"""Render ``newmark.md`` once per epy_mdr theme to HTML + PDF.

Demonstrates the full epy_mdr publishing pipeline on a feature-complete
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
:func:`epy_mdr._pdf_footer.add_footer`, and the ``header`` cells (if present)
via :func:`epy_mdr._pdf_footer.add_header`.

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

# Prefer an installed epy_mdr; fall back to the in-repo source tree so the
# example runs straight from a clone without `pip install -e .`.
try:
    from epy_mdr import themes
    from epy_mdr._pdf_footer import (
        add_footer,
        add_header,
        extract_anchor_pages,
    )
    from epy_mdr.renderer import (
        inject_page_numbers,
        normalize_page_size,
        render_markdown,
    )
    from epy_mdr.snippets import parse_front_matter
except ImportError:
    sys.path.insert(0, str(ROOT.parent.parent / "src"))
    from epy_mdr import themes
    from epy_mdr._pdf_footer import (
        add_footer,
        add_header,
        extract_anchor_pages,
    )
    from epy_mdr.renderer import (
        inject_page_numbers,
        normalize_page_size,
        render_markdown,
    )
    from epy_mdr.snippets import parse_front_matter

SOURCE = ROOT / "newmark.md"
OUT_DIR = ROOT / "_render" / "themes"

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
    return QPageLayout(
        QPageSize(size_id),
        QPageLayout.Orientation.Portrait,
        QMarginsF(15.0, 15.0, 15.0, 15.0),
        QPageLayout.Unit.Millimeter,
    )


class ThemeExporter:
    """Render one theme: two-pass HTML→PDF with page number injection."""

    MAX_WAIT_MS = 25_000
    POLL_MS = 300

    def __init__(self, theme_id: str, source: str, meta: dict, on_done) -> None:
        self.theme_id = theme_id
        self.source = source
        self.meta = meta
        self.on_done = on_done

        self.html_path = OUT_DIR / f"newmark_{theme_id}.html"
        self.pdf_path = OUT_DIR / f"newmark_{theme_id}.pdf"
        self._pass1_pdf = OUT_DIR / f"_p1_{theme_id}.pdf"
        self._tmp_html = ROOT / f"_tmp_{theme_id}.html"

        self._elapsed_ms = 0
        self._pending_pdf: Path | None = None
        self._pending_after = None
        # First physical page holding real content (after cover + indexes);
        # overlays start here and the footer renumbers content from 1.
        self._first_content_page = 1

        self.view = QWebEngineView()
        self.view.resize(900, 1200)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def go(self) -> None:
        print(f"\n=== theme: {self.theme_id} ===")
        theme = themes.get(self.theme_id)
        page_size = normalize_page_size(self.meta.get("page-size"))
        html = render_markdown(
            self.source,
            base_dir=ROOT,
            theme_css=theme.to_css(),
            paged=False,
            page_size=page_size,
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
        self.view.page().runJavaScript(
            "window._mathjax_done === true", self._on_poll_result
        )

    def _on_poll_result(self, done: bool) -> None:
        if done or self._elapsed_ms >= self.MAX_WAIT_MS:
            if not done:
                print(f"  [{self.theme_id}] MathJax timeout — printing anyway")
            else:
                print(f"  [{self.theme_id}] MathJax ready after {self._elapsed_ms} ms")
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
        if anchor_to_page:
            # All named destinations live in the body (index blocks emit
            # only links), so the smallest one is the first content page.
            # Everything before it (cover + TOC/LOF/LOT/LOE) is unnumbered
            # front matter; content page numbers restart at 1 from there.
            self._first_content_page = min(anchor_to_page.values())
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
            header_raw = self.meta.get("header") or []
            header_cells = (
                list(header_raw) if isinstance(header_raw, list) else [str(header_raw)]
            )
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
            try:
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
                    )
                    print(f"  [{self.theme_id}] footer stamped (from page {overlay_start})")
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
    source = SOURCE.read_text(encoding="utf-8")
    meta = parse_front_matter(source)

    app = QApplication.instance() or QApplication(sys.argv)
    remaining = list(themes.THEMES.keys())

    def kick_next() -> None:
        if not remaining:
            print("\nAll themes rendered.")
            app.quit()
            return
        theme_id = remaining.pop(0)
        exporter = ThemeExporter(theme_id, source, meta, on_done=kick_next)
        main._current = exporter  # type: ignore[attr-defined]
        exporter.go()

    QTimer.singleShot(0, kick_next)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
