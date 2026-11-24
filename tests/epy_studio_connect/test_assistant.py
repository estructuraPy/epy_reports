"""The assistant door: availability probe and refusal contract."""

from __future__ import annotations

import importlib.util

import pytest

from epy_reports.epy_studio_connect import assistant


def test_available_is_false_when_the_probe_raises(monkeypatch):
    """A find_spec() that fails means the capability is absent."""

    def _broken(name, *args, **kwargs):
        raise ImportError("epy_draft is broken")

    monkeypatch.setattr(importlib.util, "find_spec", _broken)
    assert assistant.available() is False


def test_create_panel_refuses_when_unavailable(monkeypatch):
    """Asking for the panel without epy_draft names what is missing."""
    monkeypatch.setattr(assistant, "available", lambda: False)
    with pytest.raises(assistant.AssistantUnavailableError, match="epy_draft"):
        assistant.create_panel()
