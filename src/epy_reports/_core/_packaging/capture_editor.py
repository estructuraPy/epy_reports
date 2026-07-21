"""Refresh the epy_reports editor screenshots (editor.png / editor_es.png).

Renders the real Fluent-styled main window with a representative document
so the bundled manual shows the current UI. Run it on the native platform
(the offscreen Qt plugin renders empty-font tofu on Windows)::

    python src/epy_reports/_core/_packaging/capture_editor.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu"
)

# Repo root: four levels above this file (_packaging -> _core ->
# epy_reports -> src -> root).
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import (  # noqa: E402
    QElapsedTimer,
    QEventLoop,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

from epy_reports._core import _i18n as i18n  # noqa: E402
from epy_reports._core._design import document_css  # noqa: E402
from epy_reports._ui import themes  # noqa: E402
from epy_reports.app import MarkdownWindow  # noqa: E402

OUT = ROOT / "src" / "epy_reports" / "_config" / "_assets" / "screenshots"

DEMO_DOC = """\
---
title: Structural design report
author: Ing. Angel Navarro-Mora M.Sc.
lang: en
---

# Materials

The characteristic strengths used throughout this report:

:::: {.stats}
::: {.stat}
**28 MPa**

[concrete f'c]{.stat-label}
:::
::: {.stat}
**420 MPa**

[steel fy]{.stat-label}
:::
::::

# Workflow

```mermaid
flowchart LR
    A[Load] --> B[Analyse]
    B --> C[Design]
```
"""


def pump(app: QApplication, ms: int) -> None:
    """Spin the event loop so async painting/rendering settles."""
    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < ms:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)


def grab(app: QApplication, win: MarkdownWindow, name: str) -> None:
    """Save a grab of the laid-out (but hidden) main window."""
    pix = win.grab()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    pix.save(str(path))
    print(f"  {name:16s} {pix.width()}x{pix.height()}  "
          f"{path.stat().st_size:,} B")


def main() -> int:
    """Boot the window off-screen and refresh the editor screenshots."""
    app = QApplication.instance() or QApplication(sys.argv)
    themes.apply_palette(app, themes.get("corporate"))
    app.setStyleSheet(themes.qss_for(themes.get("corporate")))

    win = MarkdownWindow()
    win.resize(1280, 800)
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    tab = win._current_tab()
    if tab is not None:
        tab.set_initial_text(DEMO_DOC, path=None)
        tab.set_theme_css(document_css(themes.get("corporate")))
    win.show()
    # The window restores the user's saved UI language from QSettings; force
    # English for the canonical shot before switching to Spanish.
    i18n.set_language("en")
    pump(app, 4000)

    print("English:")
    grab(app, win, "editor.png")
    print("Spanish:")
    i18n.set_language("es")
    pump(app, 400)
    grab(app, win, "editor_es.png")

    QTimer.singleShot(0, app.quit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
