"""Tests for the headless Markdown -> PDF export flow (_core/_export_pdf).

``render_report_pdf`` drives a real QWebEngineView through two Paged.js
print passes, waiting on real page-load/JS/print signals -- exactly the
kind of "opens a window or waits on a display" boundary the project's
own testing notes call out as hang-prone in an offscreen environment.
So every test here replaces QWebEngineView with a fake that fires the
same signals/callbacks from a QTimer (asynchronously, so the function's
own polling loops actually run) instead of doing a real page load, and
writes a REAL, valid multi-page PDF via reportlab where the real
QWebEngineView would have printed one.

Everything AFTER that boundary -- extracting anchors, stamping the
watermark/header/footer/metadata, joining cover/annex PDFs -- runs
through the REAL ``epy_export`` package (a sibling, already-a-dependency
package in this monorepo) against that real PDF, so those branches are
exercised faithfully rather than mocked away too.
"""

from __future__ import annotations

import base64
from pathlib import Path

import epy_export
import pytest
from PySide6 import QtWebEngineWidgets
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from reportlab.pdfgen import canvas as _canvas

from epy_reports._core._export_pdf import render_report_pdf

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    global _app
    if _app is None:
        _instance = QApplication.instance()
        _app = (
            _instance
            if isinstance(_instance, QApplication)
            else QApplication([])
        )
    return _app


# ---------------------------------------------------------------------------
# Fakes: a QWebEngineView that never opens a real page or display.
# ---------------------------------------------------------------------------


def _write_fake_pdf(path: Path, n_pages: int) -> None:
    """Write a real, valid N-page PDF -- what a real printToPdf would."""
    c = _canvas.Canvas(str(path))
    for i in range(n_pages):
        c.drawString(72, 720, f"Page {i + 1}")
        c.showPage()
    c.save()


class _FakeSignal:
    """connect()/disconnect() + a QTimer-deferred emit (see module docstring
    for why deferred rather than synchronous)."""

    def __init__(self) -> None:
        self._slot = None

    def connect(self, slot):
        self._slot = slot
        return self

    def disconnect(self, _conn=None):
        self._slot = None

    def emit(self, *args):
        if self._slot is not None:
            self._slot(*args)

    def emit_later(self, *args, delay_ms: int = 5):
        QTimer.singleShot(delay_ms, lambda: self.emit(*args))


class _FakePage:
    def __init__(self, pages: int, print_ok) -> None:
        self.pdfPrintingFinished = _FakeSignal()
        self._pages = pages
        # A single bool applies to every printToPdf call; a list gives a
        # per-call (1st pass, 2nd pass, ...) result, holding its last
        # entry once exhausted.
        self._print_ok = print_ok
        self._call = 0
        self._paged_done_polls = 0

    def runJavaScript(self, expr, callback):  # noqa: N802 - Qt API name
        # The FIRST poll of "is Paged.js done" reports "not yet" so
        # render_report_pdf's own retry loop (`while js(...) is not
        # True: pump(150)`) genuinely retries once, the same way it
        # would while pagination is still running on a real page.
        if expr == "window._paged_done === true":
            self._paged_done_polls += 1
            value = self._paged_done_polls >= 2
        else:
            value = True
        QTimer.singleShot(5, lambda: callback(value))

    def _next_result(self) -> bool:
        if isinstance(self._print_ok, list):
            index = min(self._call, len(self._print_ok) - 1)
            self._call += 1
            return self._print_ok[index]
        return self._print_ok

    def printToPdf(self, path, _layout):  # noqa: N802 - Qt API name
        ok = self._next_result()
        if ok:
            _write_fake_pdf(Path(path), self._pages)
        self.pdfPrintingFinished.emit_later(path, ok)


class _FakeWebView:
    """Stands in for QWebEngineView: no real page load, WebEngine or
    display -- just the signals/callbacks render_report_pdf polls for."""

    def __init__(self, pages: int = 2, print_ok=True) -> None:
        self.loadFinished = _FakeSignal()
        self._page = _FakePage(pages, print_ok)

    def setAttribute(self, *_a):  # noqa: N802 - Qt API name
        pass

    def resize(self, *_a):
        pass

    def show(self):
        pass

    def load(self, _url):
        self.loadFinished.emit_later(True)

    def page(self):
        return self._page

    def deleteLater(self):  # noqa: N802 - Qt API name
        pass


def _install_fake_webview(monkeypatch, **kwargs):
    monkeypatch.setattr(
        QtWebEngineWidgets, "QWebEngineView", lambda: _FakeWebView(**kwargs)
    )


_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _write_small_pdf(path: Path, n_pages: int = 1) -> None:
    _write_fake_pdf(path, n_pages)


# ---------------------------------------------------------------------------
# Early validation -- no Qt touched at all (resolve_pdf_attachments runs
# before the QApplication line)
# ---------------------------------------------------------------------------


def test_missing_cover_pdf_raises_before_any_rendering(tmp_path):
    source = "---\ntitle: T\ncover-pdf: ghost.pdf\n---\n\nBody.\n"
    with pytest.raises(FileNotFoundError):
        render_report_pdf(
            source, tmp_path / "out.pdf",
            base_dir=tmp_path, theme_css="",
        )


def test_dropped_annexes_block_sequence_raises_valueerror(tmp_path):
    """``annexes:`` followed by an indented YAML block sequence is read
    as an EMPTY value (only the key's own line is parsed) -- this must
    refuse loudly rather than silently exporting without the annexes
    the author asked for. (``annexes: []`` is the deliberate "none"
    spelling and does NOT raise -- see test_pdf_attachments.py.)
    """
    source = (
        "---\ntitle: T\nannexes:\n  - uno.pdf\n  - dos.pdf\n---\n\nBody.\n"
    )
    with pytest.raises(ValueError, match="annexes"):
        render_report_pdf(
            source, tmp_path / "out.pdf",
            base_dir=tmp_path, theme_css="",
        )


# ---------------------------------------------------------------------------
# Single-pass fallback: no named destinations in the printed PDF (a plain
# reportlab PDF genuinely has none -- this is the REAL epy_export function,
# not mocked)
# ---------------------------------------------------------------------------


def test_no_named_destinations_falls_back_to_single_pass(
    qapp, tmp_path, monkeypatch
):
    _install_fake_webview(monkeypatch, pages=3)
    out = tmp_path / "out.pdf"
    render_report_pdf(
        "# Title\n\nBody text.\n", out,
        base_dir=tmp_path, theme_css="",
    )
    assert out.exists()
    import pypdf

    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 3
    # Metadata is always stamped, even on the single-pass fallback.
    assert reader.metadata.creator == "epy_reports"


def test_no_named_destinations_with_cover_starts_page_two(
    qapp, tmp_path, monkeypatch
):
    """has_cover shifts the fallback's start_page to 2 (the cover is the
    unnumbered page 1); verified via the footer actually being stamped
    with page-numbers on, which would raise if start_page were invalid."""
    _install_fake_webview(monkeypatch, pages=2)
    out = tmp_path / "out.pdf"
    render_report_pdf(
        "---\ncover: true\npage-numbers: true\n---\n\n# T\n\nBody.\n",
        out, base_dir=tmp_path, theme_css="",
    )
    assert out.exists()


# ---------------------------------------------------------------------------
# Two-pass flow: named destinations present -> page numbers injected,
# second print pass runs.
# ---------------------------------------------------------------------------


def test_named_destinations_trigger_second_pass(qapp, tmp_path, monkeypatch):
    _install_fake_webview(monkeypatch, pages=4)
    monkeypatch.setattr(
        epy_export,
        "extract_anchor_pages",
        lambda pdf_path: {
            "toc-h-1": 1,
            "fig-a": 3,
            "epy-section-roman-1": 1,
            "epy-section-arabic-1": 3,
        },
    )
    out = tmp_path / "out.pdf"
    render_report_pdf(
        "# Title\n\nBody.\n", out, base_dir=tmp_path, theme_css="",
    )
    assert out.exists()
    import pypdf

    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) == 4


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_pass1_print_failure_raises_runtimeerror(qapp, tmp_path, monkeypatch):
    _install_fake_webview(monkeypatch, print_ok=False)
    with pytest.raises(RuntimeError, match="pass 1"):
        render_report_pdf(
            "# T\n\nBody.\n", tmp_path / "out.pdf",
            base_dir=tmp_path, theme_css="",
        )


def test_pass2_print_failure_raises_runtimeerror(qapp, tmp_path, monkeypatch):
    """pass 1 succeeds (fake) and reports named destinations, so a second
    pass is attempted on the SAME view/page (render_report_pdf builds only
    one QWebEngineView for both passes); that second printToPdf call is
    made to fail."""
    _install_fake_webview(monkeypatch, print_ok=[True, False])
    monkeypatch.setattr(
        epy_export, "extract_anchor_pages", lambda pdf_path: {"fig-a": 1}
    )
    with pytest.raises(RuntimeError, match="pass 2"):
        render_report_pdf(
            "# T\n\nBody.\n", tmp_path / "out.pdf",
            base_dir=tmp_path, theme_css="",
        )


# ---------------------------------------------------------------------------
# Stamping: watermark, header, footer, metadata (real epy_export calls)
# ---------------------------------------------------------------------------


def test_missing_final_output_raises_runtimeerror(qapp, tmp_path, monkeypatch):
    """Defensive final check: print_html's own success test already
    requires out_pdf.exists() to return True, so this simulates external
    interference AFTER the copy (e.g. concurrent cleanup / antivirus
    deleting the file) by making Path.exists() lie specifically for
    ``out`` -- every other path (including pass1, still real) answers
    truthfully.
    """
    _install_fake_webview(monkeypatch, pages=1)
    out = tmp_path / "out.pdf"
    real_exists = Path.exists

    def fake_exists(self):
        if self == out:
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    with pytest.raises(RuntimeError, match="did not complete"):
        render_report_pdf(
            "# T\n\nBody.\n", out, base_dir=tmp_path, theme_css="",
        )


def test_watermark_header_footer_and_metadata_are_stamped(
    qapp, tmp_path, monkeypatch
):
    _install_fake_webview(monkeypatch, pages=2)
    watermark = tmp_path / "wm.png"
    watermark.write_bytes(_PNG_BYTES)
    source = (
        "---\n"
        'title: "My Report"\n'
        'author: "A. Navarro"\n'
        'watermark: "wm.png"\n'
        'header: ["Left", "Right"]\n'
        'footer: "Confidential"\n'
        "page-numbers: true\n"
        "---\n\n# T\n\nBody.\n"
    )
    out = tmp_path / "out.pdf"
    render_report_pdf(source, out, base_dir=tmp_path, theme_css="")
    assert out.exists()

    import pypdf

    reader = pypdf.PdfReader(str(out))
    assert reader.metadata.title == "My Report"
    assert reader.metadata.author == "A. Navarro"


def test_page_bg_is_stamped_when_theme_declares_one(
    qapp, tmp_path, monkeypatch
):
    _install_fake_webview(monkeypatch, pages=1)
    out = tmp_path / "out.pdf"
    render_report_pdf(
        "# T\n\nBody.\n", out,
        base_dir=tmp_path, theme_css="", page_bg="#f0f0f0",
    )
    assert out.exists()


def test_watermark_path_not_a_file_is_skipped(qapp, tmp_path, monkeypatch):
    """A declared watermark that does not resolve to a real file is
    silently skipped rather than raising (only an existing file is
    stamped -- see the `if wm.is_file():` guard)."""
    _install_fake_webview(monkeypatch, pages=1)
    source = '---\nwatermark: "does-not-exist.png"\n---\n\n# T\n\nBody.\n'
    out = tmp_path / "out.pdf"
    render_report_pdf(source, out, base_dir=tmp_path, theme_css="")
    assert out.exists()


# ---------------------------------------------------------------------------
# cover-pdf / annexes joining (real epy_export.append_pdf / prepend_pdf)
# ---------------------------------------------------------------------------


def test_cover_and_annexes_are_joined(qapp, tmp_path, monkeypatch):
    _install_fake_webview(monkeypatch, pages=2)
    cover = tmp_path / "cover.pdf"
    _write_small_pdf(cover, n_pages=1)
    annex = tmp_path / "annex.pdf"
    _write_small_pdf(annex, n_pages=1)
    source = (
        "---\n"
        'cover-pdf: "cover.pdf"\n'
        'annexes: ["annex.pdf"]\n'
        "---\n\n# T\n\nBody.\n"
    )
    out = tmp_path / "out.pdf"
    render_report_pdf(source, out, base_dir=tmp_path, theme_css="")
    assert out.exists()

    import pypdf

    reader = pypdf.PdfReader(str(out))
    # 2 body pages + 1 annex (appended before stamping) + 1 cover
    # (prepended after stamping) = 4.
    assert len(reader.pages) == 4
