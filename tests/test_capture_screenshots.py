"""Tests for the screenshot-refresh dev tool (capture_screenshots).

This is a maintainer script (run manually to refresh the bundled manual's
editor.png / editor_es.png), never imported by the shipping application,
which is why it started at 0% coverage. It boots the real
``MarkdownWindow`` off-screen and writes PNGs to a package-relative
``OUT`` directory, so every test here:

* redirects ``OUT`` to ``tmp_path`` — never touches the real bundled
  screenshots under ``_config/_assets/screenshots``;
* patches ``epy_reports.app.QSettings`` to an in-memory stand-in, the same
  pattern ``tests/test_app.py`` uses — a real ``MarkdownWindow`` reads/
  writes user preferences via QSettings under the "ANM Ingeniería" scope,
  which must not touch the real per-user registry hive during a test run;
* resets the UI language back to English on teardown, since ``main()``
  deliberately leaves it in Spanish (it renders both screenshots) and
  later test modules assume the English default.
"""

from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from epy_reports import app as app_mod
from epy_reports._core import _i18n as i18n
from epy_reports._core._packaging import capture_screenshots as cs

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _instance = QApplication.instance()
        _app = (
            _instance
            if isinstance(_instance, QApplication)
            else QApplication([])
        )
    return _app


class _ScratchSettings:
    """In-memory QSettings stand-in (mirrors tests/test_app.py's)."""

    _store: dict[str, object] = {}

    def __init__(self, *_args, **_kwargs):
        self._store = _ScratchSettings._store

    def value(self, key, default=None, _type=None):
        return self._store.get(key, default)

    def setValue(self, key, value):  # noqa: N802 - Qt API name
        self._store[key] = value

    def sync(self):
        return True


@pytest.fixture
def window(qapp, monkeypatch):
    """Build a fresh, scratch-settings MarkdownWindow and tear it down."""
    monkeypatch.setattr(app_mod, "QSettings", _ScratchSettings)
    win = app_mod.MarkdownWindow()
    try:
        yield win
    finally:
        i18n.set_language("en")
        win.deleteLater()
        qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qapp.processEvents()


# ---------------------------------------------------------------------------
# Module-level content
# ---------------------------------------------------------------------------


def test_out_dir_points_at_the_bundled_screenshots_folder():
    """OUT resolves under _config/_assets/screenshots (import-time check)."""
    assert cs.OUT.parts[-3:] == ("_config", "_assets", "screenshots")


def test_demo_doc_is_a_representative_document():
    """DEMO_DOC exercises the stats block and a mermaid diagram fence."""
    assert "concrete f'c" in cs.DEMO_DOC
    assert "```mermaid" in cs.DEMO_DOC


# ---------------------------------------------------------------------------
# pump
# ---------------------------------------------------------------------------


def test_pump_blocks_for_roughly_the_requested_duration(qapp):
    """pump() spins the event loop for at least the requested time."""
    start = time.monotonic()
    cs.pump(qapp, 40)
    assert time.monotonic() - start >= 0.03


# ---------------------------------------------------------------------------
# grab
# ---------------------------------------------------------------------------


def test_grab_writes_a_pixmap_under_out_dir(
    window, qapp, tmp_path, monkeypatch
):
    """grab() creates OUT (if needed) and saves a non-empty PNG there."""
    monkeypatch.setattr(cs, "OUT", tmp_path / "shots")
    window.resize(300, 200)
    cs.grab(qapp, window, "sample.png")
    out_file = tmp_path / "shots" / "sample.png"
    assert out_file.is_file()
    assert out_file.stat().st_size > 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def test_main_renders_english_and_spanish_screenshots(
    qapp, tmp_path, monkeypatch
):
    """main() produces both screenshots and returns 0.

    ``pump`` is stubbed to a single processEvents() call so the test does
    not actually wait out the real 4s/400ms settling delays the script
    uses when run by hand. The MarkdownWindow ``main()`` builds internally
    is tracked and safely torn down afterwards (deleteLater + flush) --
    left for the session-end teardown to reap, its live WebEngine preview
    child crashed the process with an access violation (confirmed by
    running this test without the explicit teardown below).
    """
    monkeypatch.setattr(app_mod, "QSettings", _ScratchSettings)
    monkeypatch.setattr(cs, "OUT", tmp_path / "shots")
    monkeypatch.setattr(cs, "pump", lambda app, ms: app.processEvents())
    created: list = []
    real_ctor = cs.MarkdownWindow

    def _tracking_ctor(*args, **kwargs):
        win = real_ctor(*args, **kwargs)
        created.append(win)
        return win

    monkeypatch.setattr(cs, "MarkdownWindow", _tracking_ctor)
    try:
        exit_code = cs.main()
        assert exit_code == 0
        assert (tmp_path / "shots" / "editor.png").is_file()
        assert (tmp_path / "shots" / "editor_es.png").is_file()
    finally:
        i18n.set_language("en")
        qapp.processEvents()  # let the scheduled app.quit() singleShot fire
        for win in created:
            win.deleteLater()
        qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qapp.processEvents()
