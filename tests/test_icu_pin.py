"""Tests for the Windows system-ICU pin in the package bootstrap.

The pin runs at import time; these tests assert it is harmless to re-run
and that Qt actually imports afterwards (the regression this guards against
is ``ImportError: DLL load failed ... WinError 127`` from conda's ICU
shadowing the Windows one).
"""

from epy_reports import _pin_system_icu


def test_pin_system_icu_reentrant():
    """Calling the pin again after package import must be a no-op."""
    _pin_system_icu()
    _pin_system_icu()


def test_qt_imports_after_pin():
    """PySide6 Qt modules must load once the package pinned the system ICU."""
    from PySide6 import QtCore, QtWidgets  # noqa: F401

    assert QtCore.qVersion()
