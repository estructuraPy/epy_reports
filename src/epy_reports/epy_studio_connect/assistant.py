"""The assistant capability as exposed by the ePy Studio contract.

The app does not import epy_draft's UI or provider layer directly. It
asks this module whether the capability is present and, when it is,
builds the shared panel. This is the only door the interface uses.
"""

from __future__ import annotations

import importlib.util
from typing import Any

__all__ = ["AssistantUnavailableError", "available", "create_panel"]


class AssistantUnavailableError(RuntimeError):
    """epy_draft or its assistant panel is not installed."""


def available() -> bool:
    """Return whether the shared assistant panel can be imported."""
    try:
        return importlib.util.find_spec("epy_draft._ui.assistant") is not None
    except (ImportError, ValueError):
        return False


def create_panel(**kwargs: Any) -> Any:
    """Build the shared assistant panel, or name what is missing."""
    if not available():
        raise AssistantUnavailableError(
            "epy_draft is not installed: the assistant needs its panel and "
            "provider layer."
        )
    from epy_draft._ui.assistant import AssistantPanel  # noqa: PLC0415

    return AssistantPanel(**kwargs)
