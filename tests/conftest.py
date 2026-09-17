r"""Shared pytest fixtures for the epy_reports test-suite.

The Qt platform is forced to ``offscreen`` before any ``QApplication`` is
constructed, so the widget and dialog tests run headlessly on CI without a
display server.

``epy_reports`` is imported here — before any test module — so its
``_pin_system_icu()`` bootstrap runs ahead of every ``PySide6`` import.
Several test files import ``PySide6.QtWidgets`` at module level before
importing the package; without this, running one of those files standalone
dies with ``ImportError ... WinError 127`` in conda environments (conda's
``Library\bin`` ICU shadows the Windows system ICU that Qt links against).
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

import epy_reports  # noqa: E402, F401  — must precede any PySide6 import (ICU pin)


@pytest.fixture(scope="session", autouse=True)
def _qt_session_teardown():
    """Destroy the QApplication before interpreter shutdown.

    Test modules keep module-global ``QApplication`` instances alive until
    process exit; Qt's native teardown then races Python finalization and
    dies with an access violation (0xC0000005) after all tests have passed.
    Deleting the C++ object while the interpreter is still healthy avoids
    the crash. No-op when Qt was never loaded.
    """
    yield
    if "PySide6.QtWidgets" not in sys.modules:
        return
    from PySide6.QtWidgets import QApplication  # noqa: PLC0415

    app = QApplication.instance()
    if app is None:
        return
    import shiboken6  # noqa: PLC0415

    # Widgets first, app last: deleting the QApplication while top-level
    # widgets are still alive is itself an access violation. Delete the C++
    # objects directly instead of close()-ing them — close() runs Python
    # closeEvent handlers (e.g. the main window's confirm-on-close logic)
    # against test state that is already torn down.
    for widget in QApplication.topLevelWidgets():
        if shiboken6.isValid(widget):
            shiboken6.delete(widget)
    app.processEvents()
    app.processEvents()
    shiboken6.delete(app)


@pytest.fixture(autouse=True, scope="session")
def _never_open_a_browser():
    """No test may open a browser tab, whatever it passes for display.

    Plotly's ``fig.show()`` outside a notebook does not draw anything locally:
    it starts an ephemeral HTTP server on 127.0.0.1, points the default
    browser at it, and blocks until that one request arrives. A test run that
    opens tabs is a test run nobody can leave unattended.

    Installed in EVERY repo rather than only where a scan found display calls.
    Going by scan is what let the tabs come back twice: a regex missed six
    repos because it could not cross a line end, and the AST scan that
    replaced it still only sees a display keyword passed as a literal ``True``
    -- one passed positionally, through a variable or from a parametrize list
    is invisible to both. The fixture is inert where nothing displays, so
    predicting which repos need it buys nothing and costs a recurrence.

    The branch under test still executes and still counts as covered; it just
    cannot reach a browser. This is the half the housekeeper's Rule 14 audits
    cannot see -- they read library ``src/``, and this lives in ``tests/``.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        yield
        return

    original = go.Figure.show
    go.Figure.show = lambda self, *args, **kwargs: None
    try:
        yield
    finally:
        go.Figure.show = original
