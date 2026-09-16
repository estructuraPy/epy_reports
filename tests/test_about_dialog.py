"""Tests for branding resources, ICO file, and AboutDialog.

Checks:
- Three branding images are resolvable via importlib.resources and
  return non-empty bytes.
- The ICO file at src/epy_reports/_core/_packaging/assets_build/epy_reports.ico
  has exactly 4 size entries (parsed from the ICONDIR binary header).
- AboutDialog is importable without a QApplication crash, instantiates
  without error, and contains the expected author strings in its labels.
"""

from __future__ import annotations

import importlib.resources
import struct
from pathlib import Path

import pytest
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from epy_reports._ui.about_dialog import AboutDialog, _load_branding_pixmap

# ---------------------------------------------------------------------------
# Module-scoped QApplication (required for any QWidget instantiation)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 2 — branding resources resolvable via importlib.resources
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", [
    "epy_reports.png",
    "estructurapy.png",
    "imagotipo_anm.png",
])
def test_branding_resource_non_empty(filename: str):
    """Each branding image resolves via importlib.resources."""
    pkg = importlib.resources.files("epy_reports._config._assets.branding")
    data = (pkg / filename).read_bytes()
    assert len(data) > 0, f"{filename} is empty"


def test_load_branding_pixmap_returns_real_image(qapp):
    """A real, bundled branding file loads into a non-null QPixmap."""
    pixmap = _load_branding_pixmap("epy_reports.png")
    assert not pixmap.isNull()
    assert pixmap.width() > 0


def test_load_branding_pixmap_missing_resource_returns_empty_pixmap(
    qapp, monkeypatch
):
    """A resource lookup failure is absorbed, not raised.

    ``_load_branding_pixmap`` must keep the About dialog usable even if the
    package data is missing or the environment cannot resolve resources
    (e.g. a broken frozen build); it degrades to a blank QPixmap instead of
    crashing the dialog open.
    """

    def _raise(*args, **kwargs):
        raise FileNotFoundError("no such resource package")

    monkeypatch.setattr(importlib.resources, "files", _raise)
    pixmap = _load_branding_pixmap("epy_reports.png")
    assert isinstance(pixmap, QPixmap)
    assert pixmap.isNull()


# ---------------------------------------------------------------------------
# Task 1 — ICO file has 4 size entries
# ---------------------------------------------------------------------------

def test_ico_has_four_sizes():
    """_core/_packaging/assets_build/epy_reports.ico ICONDIR count == 4."""
    ico_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "epy_reports"
        / "_core"
        / "_packaging"
        / "assets_build"
        / "epy_reports.ico"
    )
    assert ico_path.exists(), f"ICO not found: {ico_path}"
    with open(ico_path, "rb") as fh:
        _reserved, _type, count = struct.unpack("<HHH", fh.read(6))
    assert count == 4, f"Expected 4 ICO sizes, got {count}"


# ---------------------------------------------------------------------------
# Task 4 — AboutDialog instantiates and contains author strings
# ---------------------------------------------------------------------------

def test_about_dialog_author_strings(qapp):
    """AboutDialog contains expected author and email strings in its labels."""
    dlg = AboutDialog()
    all_label_text = " ".join(
        lbl.text()
        for lbl in dlg.findChildren(QLabel)
    )
    assert "Navarro-Mora" in all_label_text, (
        "Author name not found in AboutDialog labels"
    )
    assert "anmingenieria.com" in all_label_text, (
        "Author email not found in AboutDialog labels"
    )
