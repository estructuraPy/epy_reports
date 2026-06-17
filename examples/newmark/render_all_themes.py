"""Render ``newmark.md`` once per epy_mdr theme to HTML + PDF.

Demonstrates the full epy_mdr publishing pipeline on a feature-complete
document: YAML front matter with cover page, TOC/LOF/LOT/LOE index markers,
page breaks, footnotes, IEEE bibliography, Quarto cross-references
(``@sec-``/``@fig-``/``@eq-``), titled callouts, figures, tables and
display equations. Each theme is rendered with its own ``:root { … }`` block
(``Theme.to_css()``), then printed to PDF via Qt WebEngine after MathJax
finishes typesetting.

Run it from this directory::

    python render_all_themes.py

Output lands in ``_render/themes/`` (git-ignored).

Typography note
---------------
The PDFs use the fonts each theme requests **only when those font families
are installed on the machine doing the render**. On a PC missing a given
family, Qt/Pandoc fall back to the nearest available font, so the same
document may look slightly different across machines. Layout, colors,
spacing and structure are theme-defined and stable; only the glyph shapes
depend on locally available fonts.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QMarginsF, QTimer, QUrl
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent

# Prefer an installed epy_mdr; fall back to the in-repo source tree so the
# example runs straight from a clone without `pip install -e .`.
try:
    from epy_mdr import themes
    from epy_mdr.renderer import render_markdown
except ImportError:
    sys.path.insert(0, str(ROOT.parent.parent / "src"))
    from epy_mdr import themes
    from epy_mdr.renderer import render_markdown

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


class ThemeExporter:
    """Render one theme to HTML + PDF, then call ``on_done``."""

    def __init__(self, theme_id: str, source: str, on_done) -> None:
        self.theme_id = theme_id
        self.source = source
        self.on_done = on_done
        self.html_path = OUT_DIR / f"newmark_{theme_id}.html"
        self.pdf_path = OUT_DIR / f"newmark_{theme_id}.pdf"
        self.live_html = ROOT / f"_preview_newmark_{theme_id}.html"
        self.elapsed_ms = 0
        self.max_wait_ms = 25_000
        self.poll_interval_ms = 300
        self.view = QWebEngineView()
        self.view.resize(900, 1200)
        self.view.loadFinished.connect(self._on_load)

    def go(self) -> None:
        print(f"\n=== theme: {self.theme_id} ===")
        theme = themes.get(self.theme_id)
        html = render_markdown(
            self.source,
            base_dir=ROOT,
            theme_css=theme.to_css(),
            paged=True,
            page_size="letter",
        )
        self.html_path.write_text(html, encoding="utf-8")
        print(f"  HTML -> {self.html_path.name}  ({len(html)} chars)")
        # setHtml() is capped at ~2 MB and the inline MathJax bundle blows
        # past it; load via file:// so relative svg/jpg also resolve.
        self.live_html.write_text(html, encoding="utf-8")
        self.view.load(QUrl.fromLocalFile(str(self.live_html.resolve())))

    def _on_load(self, ok: bool) -> None:
        if not ok:
            print("  PDF  -> load failed")
            self._finish()
            return
        self.view.page().runJavaScript(WAIT_FOR_MATHJAX_JS)
        QTimer.singleShot(self.poll_interval_ms, self._poll)

    def _poll(self) -> None:
        self.elapsed_ms += self.poll_interval_ms
        self.view.page().runJavaScript(
            "window._mathjax_done === true", self._on_poll_result
        )

    def _on_poll_result(self, done: bool) -> None:
        if done:
            print(f"  MathJax ready after {self.elapsed_ms} ms")
            QTimer.singleShot(300, self._print_pdf)
            return
        if self.elapsed_ms >= self.max_wait_ms:
            print(f"  MathJax timeout {self.elapsed_ms} ms — printing anyway")
            self._print_pdf()
            return
        QTimer.singleShot(self.poll_interval_ms, self._poll)

    def _print_pdf(self) -> None:
        page = self.view.page()
        page.pdfPrintingFinished.connect(self._on_pdf_done)
        layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.Letter),
            QPageLayout.Orientation.Portrait,
            QMarginsF(15, 15, 15, 15),
        )
        page.printToPdf(str(self.pdf_path), layout)

    def _on_pdf_done(self, path: str, ok: bool) -> None:
        size = self.pdf_path.stat().st_size if self.pdf_path.exists() else 0
        print(f"  PDF  -> {self.pdf_path.name}  ok={ok}  ({size} bytes)")
        self._finish()

    def _finish(self) -> None:
        try:
            self.live_html.unlink()
        except OSError:
            pass
        self.on_done()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text(encoding="utf-8")
    app = QApplication.instance() or QApplication(sys.argv)
    remaining = list(themes.THEMES.keys())

    def kick_next() -> None:
        if not remaining:
            print("\nAll themes rendered.")
            app.quit()
            return
        theme_id = remaining.pop(0)
        exporter = ThemeExporter(theme_id, source, on_done=kick_next)
        main._current = exporter  # type: ignore[attr-defined]
        exporter.go()

    QTimer.singleShot(0, kick_next)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
