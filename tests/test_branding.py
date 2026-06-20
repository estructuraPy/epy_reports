"""Tests for branding resources, ICO file, and AboutDialog.

Checks:
- Three branding images are resolvable via importlib.resources and
  return non-empty bytes.
- The ICO file at assets_build/epy_reports.ico has exactly 4 size entries
  (parsed from the ICONDIR binary header).
- AboutDialog is importable without a QApplication crash, instantiates
  without error, and contains the expected author strings in its labels.
"""

from __future__ import annotations

import importlib.resources
import struct
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from epy_reports.about_dialog import AboutDialog

# ---------------------------------------------------------------------------
# Module-scoped QApplication (required for any QWidget instantiation)
# ---------------------------------------------------------------------------

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
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
    pkg = importlib.resources.files("epy_reports.assets.branding")
    data = (pkg / filename).read_bytes()
    assert len(data) > 0, f"{filename} is empty"


# ---------------------------------------------------------------------------
# Task 1 — ICO file has 4 size entries
# ---------------------------------------------------------------------------

def test_ico_has_four_sizes():
    """assets_build/epy_reports.ico ICONDIR count == 4."""
    ico_path = (
        Path(__file__).resolve().parent.parent
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
