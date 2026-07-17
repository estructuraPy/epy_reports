"""Tests for the lightweight in-app internationalization module."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from epy_reports import _i18n as i18n

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


@pytest.fixture(autouse=True)
def _restore_language():
    """Ensure each test starts and ends in English."""
    i18n.set_language("en")
    yield
    i18n.set_language("en")


# ---------------------------------------------------------------------------
# tr / set_language / current_language
# ---------------------------------------------------------------------------


def test_tr_identity_in_english():
    """In English, tr is the identity function."""
    assert i18n.tr("Save") == "Save"


def test_dead_widget_observer_dropped_on_language_switch():
    """An observer whose Qt object died is removed instead of raising.

    Windows register relabel callbacks but nothing unregisters them on
    destruction; the registry must self-heal on the shiboken
    'already deleted' failure and keep notifying the healthy observers.
    """
    calls = []

    def dead_observer():
        raise RuntimeError(
            "libshiboken: Internal C++ object (QAction) already deleted."
        )

    def live_observer():
        calls.append(i18n.current_language())

    i18n._observers.append(dead_observer)
    i18n._observers.append(live_observer)
    try:
        i18n.set_language("es")
        assert dead_observer not in i18n._observers
        assert calls == ["es"]
        i18n.set_language("en")
        assert calls == ["es", "en"]
    finally:
        for cb in (dead_observer, live_observer):
            if cb in i18n._observers:
                i18n._observers.remove(cb)


def test_other_runtime_errors_still_propagate():
    """Only the shiboken already-deleted failure is absorbed."""

    def broken_observer():
        raise RuntimeError("boom")

    i18n._observers.append(broken_observer)
    try:
        with pytest.raises(RuntimeError, match="boom"):
            i18n.set_language("es")
        assert broken_observer in i18n._observers
    finally:
        i18n._observers.remove(broken_observer)
        i18n.set_language("en")


def test_tr_translates_in_spanish():
    """In Spanish, known keys are translated."""
    i18n.set_language("es")
    assert i18n.tr("Save") == "Guardar"


def test_tr_unknown_key_falls_back():
    """An unknown key passes through unchanged in Spanish."""
    i18n.set_language("es")
    assert i18n.tr("Totally unknown phrase") == "Totally unknown phrase"


def test_current_language_reflects_switch():
    """``current_language`` reports the active code."""
    i18n.set_language("es")
    assert i18n.current_language() == "es"


def test_set_language_ignores_unknown_code():
    """An unsupported code is a no-op."""
    i18n.set_language("fr")
    assert i18n.current_language() == "en"


def test_set_language_same_code_is_noop():
    """Setting the already-active language does not fire observers."""
    fired: list[int] = []
    i18n.on_language_changed(lambda: fired.append(1))
    i18n.set_language("en")  # already en
    assert fired == []


# ---------------------------------------------------------------------------
# observers
# ---------------------------------------------------------------------------


def test_observer_fires_on_change():
    """A registered observer runs when the language changes."""
    fired: list[str] = []
    i18n.on_language_changed(lambda: fired.append(i18n.current_language()))
    i18n.set_language("es")
    assert fired == ["es"]


# ---------------------------------------------------------------------------
# translate_widget
# ---------------------------------------------------------------------------


def test_translate_widget_noop_in_english(qapp):
    """In English the widget tree is untouched."""
    w = QWidget()
    lbl = QLabel("Save", w)
    i18n.translate_widget(w)
    assert lbl.text() == "Save"


def test_translate_widget_relabels_children(qapp):
    """In Spanish, labels / buttons / group titles / placeholders change."""
    i18n.set_language("es")
    w = QWidget()
    w.setWindowTitle("Document properties")
    layout = QVBoxLayout(w)
    label = QLabel("Title:", w)
    button = QPushButton("Cancel", w)
    box = QGroupBox("Footer", w)
    edit = QLineEdit(w)
    edit.setPlaceholderText("Figure caption")
    for child in (label, button, box, edit):
        layout.addWidget(child)

    i18n.translate_widget(w)

    assert w.windowTitle() == "Propiedades del documento"
    assert label.text() == "Título:"
    assert button.text() == "Cancelar"
    assert box.title() == "Pie de página"
    assert edit.placeholderText() == "Título de la figura"
