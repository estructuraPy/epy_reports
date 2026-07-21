"""Tests for the config-templates default directory resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports._core import templates

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance.

    ``_config_base_dir`` reads ``QStandardPaths`` which requires a Qt
    application context to resolve the writable config location.
    """
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_config_base_dir_under_app_namespace(qapp):
    """The default templates dir lives under the epy_reports config tree."""
    path = templates._config_base_dir()
    assert isinstance(path, Path)
    assert path.parts[-2:] == ("epy_reports", "templates")


def test_resolve_base_prefers_explicit(qapp, tmp_path):
    """An explicit base_dir overrides the config default."""
    assert templates._resolve_base(tmp_path) == tmp_path


def test_resolve_base_falls_back_to_config(qapp):
    """A None base_dir resolves to the config location."""
    assert templates._resolve_base(None) == templates._config_base_dir()


def test_save_uses_config_dir_when_no_base(qapp, monkeypatch, tmp_path):
    """save_template lands in the resolved config dir when no base given."""
    target = tmp_path / "cfg-templates"
    monkeypatch.setattr(templates, "_config_base_dir", lambda: target)
    templates.save_template("Default Dir", {"theme": "corporate"})
    assert (target / "Default Dir.json").exists()
    assert "Default Dir" in templates.list_templates()
