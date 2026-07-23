"""Tests for the DocsExportDialog widget and its render worker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports._ui import docs_export_dialog as ded
from epy_reports._ui.docs_export_dialog import DocsExportDialog, _RenderWorker

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


@pytest.fixture
def stub_bridge(monkeypatch):
    """Stub the docs_bridge layout/doctype listings."""
    import epy_reports.epy_suite_connect.adapters.docs_bridge as bridge

    monkeypatch.setattr(
        bridge, "list_layouts", lambda: ["corporate", "ieee"]
    )
    monkeypatch.setattr(
        bridge, "list_document_types", lambda: ["report", "article"]
    )


# ---------------------------------------------------------------------------
# Dialog construction + properties
# ---------------------------------------------------------------------------


def test_dialog_populates_combos(qapp, stub_bridge):
    """Layout and document-type combos list the bridge values."""
    dlg = DocsExportDialog(Path("doc.md"))
    layouts = [
        dlg._combo_layout.itemText(i)
        for i in range(dlg._combo_layout.count())
    ]
    assert "corporate" in layouts
    assert "ieee" in layouts


def test_default_output_dir_is_source_results(qapp, stub_bridge, tmp_path):
    """The default output directory hangs off the source's results/."""
    src = tmp_path / "doc.md"
    with patch.object(ded.QSettings, "value", side_effect=lambda k, d: d):
        dlg = DocsExportDialog(src)
    assert dlg.output_dir == tmp_path / "results"


def test_format_checkbox_defaults(qapp, stub_bridge):
    """PDF and HTML default on, DOCX off."""
    dlg = DocsExportDialog(Path("doc.md"))
    assert dlg.export_pdf is True
    assert dlg.export_html is True
    assert dlg.export_docx is False


def test_properties_reflect_widget_state(qapp, stub_bridge):
    """The public properties echo the widget values."""
    dlg = DocsExportDialog(Path("doc.md"))
    dlg._combo_layout.setCurrentText("ieee")
    dlg._combo_doctype.setCurrentText("article")
    dlg._edit_outdir.setText(str(Path("out").resolve()))
    assert dlg.layout_name == "ieee"
    assert dlg.document_type == "article"
    assert dlg.output_dir == Path("out").resolve()


# ---------------------------------------------------------------------------
# Worker thread (run() called directly, no event loop)
# ---------------------------------------------------------------------------


def test_worker_emits_ok_on_success(qapp, monkeypatch):
    """A successful render emits finished_ok with the output dir."""
    import epy_reports.epy_suite_connect.adapters.docs_bridge as bridge

    monkeypatch.setattr(
        bridge, "render_document", lambda **kw: None
    )
    worker = _RenderWorker(
        Path("src.md"), "corporate", "report", Path("out"),
        pdf=True, html=False,
    )
    received: list[str] = []
    worker.finished_ok.connect(received.append)
    worker.run()
    assert received == [str(Path("out"))]


def test_worker_emits_err_on_failure(qapp, monkeypatch):
    """A failing render emits finished_err with the message."""
    import epy_reports.epy_suite_connect.adapters.docs_bridge as bridge

    def _boom(**kw):
        raise RuntimeError("render exploded")

    monkeypatch.setattr(bridge, "render_document", _boom)
    worker = _RenderWorker(
        Path("src.md"), "corporate", "report", Path("out"),
        pdf=True, html=True,
    )
    errors: list[str] = []
    worker.finished_err.connect(errors.append)
    worker.run()
    assert errors == ["render exploded"]
