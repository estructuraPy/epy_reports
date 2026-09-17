"""The packaging tools' ``__main__`` trailers + make_icon's Pillow guard.

Same technique as ``epy_papers/tests/test_packaging_main_guards.py``: compile
the REAL source with its REAL path (so coverage attributes the executed lines
to the file being measured), then exec it with a ``__file__`` pointing under
``tmp_path``. ``__file__`` is a plain global the tools' own path arithmetic
reads -- independent of the filename baked into the compiled code object -- so
the guard runs, the paths resolve somewhere harmless, and nothing under
``src/`` is touched.

Every path-redirection here is proven, not assumed: the bundled artefact's
mtime is recorded before and asserted unchanged after.
"""

from __future__ import annotations

import shutil
import sys
import types
from pathlib import Path

import pytest
from PySide6 import QtCore, QtWidgets


def _run_as_main(module, fake_file: Path) -> None:
    """Execute ``module``'s real source as ``__main__`` with a fake path."""
    real = Path(module.__file__)
    code = compile(real.read_text(encoding="utf-8"), str(real), "exec")
    exec(code, {"__name__": "__main__", "__file__": str(fake_file)})


def _fake_packaging_file(tmp_path: Path, *tail: str) -> Path:
    target = tmp_path.joinpath(*tail)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


# ── make_icon: Pillow import guard ───────────────────────────────────────


def test_make_icon_raises_a_clear_systemexit_without_pillow(monkeypatch):
    from epy_reports._core._packaging import make_icon as mi

    monkeypatch.setitem(sys.modules, "PIL", None)  # `from PIL import Image` -> ImportError
    real = Path(mi.__file__)
    code = compile(real.read_text(encoding="utf-8"), str(real), "exec")
    with pytest.raises(SystemExit, match="Pillow is required"):
        exec(code, {"__name__": "mi_under_test", "__file__": str(real)})


# ── make_icon: __main__ trailer ──────────────────────────────────────────


def _stage_fake_icon_source(module, tmp_path: Path) -> Path:
    fake_root = tmp_path / "_packaging"
    fake_assets = fake_root / "assets_build"
    fake_assets.mkdir(parents=True)
    shutil.copyfile(Path(module.SRC_PNG), fake_assets / Path(module.SRC_PNG).name)
    return fake_root


def test_make_icon_trailer_generates_icons_under_the_fake_root(tmp_path, capsys):
    from epy_reports._core._packaging import make_icon as mi

    fake_root = _stage_fake_icon_source(mi, tmp_path)

    _run_as_main(mi, fake_root / "make_icon" / "__init__.py")

    out = capsys.readouterr().out
    assert "Generating epy_reports icons" in out
    assert "Done." in out
    assert (fake_root / "assets_build" / "epy_reports.ico").is_file()


def test_make_icon_trailer_does_not_touch_the_bundled_icon(tmp_path):
    from epy_reports._core._packaging import make_icon as mi

    real_ico = Path(mi.OUT_DIR) / "epy_reports.ico"
    assert real_ico.exists(), f"no bundled icon at {real_ico}"
    before = real_ico.stat().st_mtime_ns

    fake_root = _stage_fake_icon_source(mi, tmp_path)
    _run_as_main(mi, fake_root / "make_icon" / "__init__.py")

    assert real_ico.stat().st_mtime_ns == before, "it wrote over the bundled icon"


# ── make_reference_docx: __main__ trailer ────────────────────────────────


def test_make_reference_docx_trailer_writes_under_the_fake_root(tmp_path):
    from epy_reports._core._packaging import make_reference_docx as mr

    def _stamps() -> dict[str, int]:
        if not Path(mr.OUT_DIR).is_dir():
            return {}
        return {p.name: p.stat().st_mtime_ns for p in Path(mr.OUT_DIR).glob("*.docx")}

    before = _stamps()

    fake_file = _fake_packaging_file(
        tmp_path, "src", "epy_reports", "_core", "_packaging",
        "make_reference_docx", "__init__.py",
    )
    with pytest.raises(SystemExit) as excinfo:
        _run_as_main(mr, fake_file)  # the trailer is `raise SystemExit(main())`
    assert excinfo.value.code == 0

    written = list(tmp_path.rglob("*.docx"))
    assert written, "the trailer ran but wrote no reference document"
    assert _stamps() == before, "it overwrote the bundled reference documents"


# ── app.py: __main__ trailer ─────────────────────────────────────────────


def test_app_trailer_exits_through_main(monkeypatch, tmp_path, capsys):
    from epy_reports import app as app_mod

    monkeypatch.setattr(sys, "argv", ["epy_reports", "--help"])
    real = Path(app_mod.__file__)
    code = compile(real.read_text(encoding="utf-8"), str(real), "exec")
    with pytest.raises(SystemExit):
        exec(code, {"__name__": "__main__", "__file__": str(tmp_path / "app.py")})
    capsys.readouterr()  # drain argparse's --help output


# ── capture_screenshots: __main__ trailer + the fresh-QApplication branch ─


class _FakePixmap:
    def save(self, path) -> None:
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")

    def width(self) -> int:
        return 10

    def height(self) -> int:
        return 10


class _FakeWindow:
    def resize(self, *args) -> None:
        pass

    def setAttribute(self, *args) -> None:
        pass

    def _current_tab(self):
        return None

    def show(self) -> None:
        pass

    def grab(self) -> _FakePixmap:
        return _FakePixmap()


def test_capture_screenshots_trailer_bootstraps_a_fresh_qapplication(
    monkeypatch, tmp_path, capsys
):
    from epy_reports import app as app_mod
    from epy_reports._core import _design, themes
    from epy_reports._core._packaging import capture_screenshots as cs

    calls: dict = {}

    class _FakeApp:
        def setStyleSheet(self, qss) -> None:
            calls["qss"] = qss

        def processEvents(self, *args):
            return True

        def quit(self) -> None:
            calls["quit"] = True

    fake_app = _FakeApp()

    class _FakeQApplication:
        @staticmethod
        def instance():
            return None  # -> main() takes the fresh-QApplication branch

        def __new__(cls, argv):
            calls["argv"] = argv
            return fake_app

    # The re-executed module imports these names, so patch at their SOURCES.
    monkeypatch.setattr(QtWidgets, "QApplication", _FakeQApplication)
    monkeypatch.setattr(app_mod, "MarkdownWindow", _FakeWindow)
    monkeypatch.setattr(themes, "apply_palette", lambda app, theme: None)
    monkeypatch.setattr(themes, "qss_for", lambda theme: "")
    monkeypatch.setattr(themes, "get", lambda name: object())
    monkeypatch.setattr(_design, "document_css", lambda theme: "")
    monkeypatch.setattr(QtCore, "QTimer", types.SimpleNamespace(singleShot=lambda ms, cb: None))

    fake_file = _fake_packaging_file(
        tmp_path, "src", "epy_reports", "_core", "_packaging",
        "capture_screenshots", "__init__.py",
    )

    with pytest.raises(SystemExit) as excinfo:
        _run_as_main(cs, fake_file)

    assert excinfo.value.code == 0
    assert "argv" in calls  # the fresh QApplication was constructed
    shots = tmp_path / "src" / "epy_reports" / "_config" / "_assets" / "screenshots"
    assert (shots / "editor.png").is_file()
    assert (shots / "editor_es.png").is_file()
    capsys.readouterr()
