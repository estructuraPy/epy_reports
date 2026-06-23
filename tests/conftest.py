"""Shared pytest fixtures for the epy_reports test-suite.

The Qt platform is forced to ``offscreen`` before any ``QApplication`` is
constructed, so the widget and dialog tests run headlessly on CI without a
display server.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
