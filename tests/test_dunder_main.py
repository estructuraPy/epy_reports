"""Tests for the ``python -m epy_reports`` entry point.

``__main__.py`` only wires ``epy_reports.app.main`` into a process exit
code; ``app.main`` itself (the real GUI bootstrap) is exercised by
``tests/test_app.py``. Here we prove the module-level plumbing: run as
``__main__`` it calls ``main()`` and turns its return value into the
process exit code via ``SystemExit``.
"""

from __future__ import annotations

import runpy

import pytest


def test_dunder_main_calls_app_main_and_exits_with_its_return_code(
    monkeypatch,
):
    """Running the module as __main__ raises SystemExit(app.main())."""
    import epy_reports.app as app_module

    monkeypatch.setattr(app_module, "main", lambda: 0)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("epy_reports.__main__", run_name="__main__")
    assert excinfo.value.code == 0


def test_dunder_main_propagates_a_nonzero_exit_code(monkeypatch):
    """A non-zero return from app.main() becomes the process exit code.

    Counter-example to the happy path above: the plumbing must not
    swallow or normalise a failure code to 0.
    """
    import epy_reports.app as app_module

    monkeypatch.setattr(app_module, "main", lambda: 7)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("epy_reports.__main__", run_name="__main__")
    assert excinfo.value.code == 7
