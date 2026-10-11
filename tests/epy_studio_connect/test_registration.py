"""The register / unregister / launch-hint contract."""

from __future__ import annotations

from epy_reports.epy_studio_connect import _registration as reg
from epy_reports.epy_studio_connect._manifest import StudioManifest

_DEMO = StudioManifest(
    app_id="demo",
    display="Demo",
    description="a demo application",
    component="demo",
    register="openwith",
    document_types=("md",),
)

_DEFAULT = StudioManifest(
    app_id="demo",
    display="Demo",
    description="a demo application",
    component="demo",
    register="default",
    document_types=("md", "markdown"),
)

_NONE = StudioManifest(
    app_id="demo",
    display="Demo",
    description="a demo application",
    component="demo",
    register="none",
)


def test_register_when_nothing_is_claimed(monkeypatch) -> None:
    """An application that claims nothing says so out loud."""
    monkeypatch.setattr(reg, "manifest", lambda: _NONE)
    assert reg.register() == [
        "demo: claims no document type; nothing to register."
    ]


def test_unregister_when_nothing_was_claimed(monkeypatch) -> None:
    """Unregistering an application that claimed nothing says so."""
    monkeypatch.setattr(reg, "manifest", lambda: _NONE)
    assert reg.unregister() == [
        "demo: claims no document type; nothing was registered to remove."
    ]


def test_register_matches_the_shipped_manifest() -> None:
    """The shipped application registers its types or says it claims none."""
    lines = reg.register()
    if reg.manifest().registers:
        assert lines[0].startswith("epy_reports: registers ")
        assert lines[1].startswith("  .")
    else:
        assert lines == [
            "epy_reports: claims no document type; nothing to register."
        ]


def test_unregister_matches_the_shipped_manifest() -> None:
    """Unregistering reports what was removed, or that nothing was."""
    lines = reg.unregister()
    if reg.manifest().registers:
        assert lines[0].startswith("epy_reports: registration removed for ")
    else:
        assert lines == [
            "epy_reports: claims no document type; nothing was registered "
            "to remove."
        ]


def test_launch_hint_is_json_ready() -> None:
    """The hint carries the app id and the entry point."""
    hint = reg.launch_hint()
    assert hint["app_id"] == "epy_reports"
    assert hint["entry_point"] == "epy_reports.app"


def test_register_openwith(monkeypatch) -> None:
    """An openwith application advertises its extensions, not the default."""
    monkeypatch.setattr(reg, "manifest", lambda: _DEMO)
    lines = reg.register()
    assert lines[0] == "demo: registers md as openwith."
    assert "  .md -> demo" in lines


def test_register_default_with_as_default(monkeypatch) -> None:
    """``--as-default`` promotes a default-capable application."""
    monkeypatch.setattr(reg, "manifest", lambda: _DEFAULT)
    lines = reg.register(["--as-default"])
    assert lines[0] == "demo: registers md,markdown as default."
    assert len(lines) == 3


def test_register_default_without_the_flag_stays_openwith(
    monkeypatch,
) -> None:
    """Without ``--as-default`` even a default-capable app is openwith."""
    monkeypatch.setattr(reg, "manifest", lambda: _DEFAULT)
    lines = reg.register([])
    assert lines[0] == "demo: registers md,markdown as openwith."


def test_unregister_with_a_claim(monkeypatch) -> None:
    """An application that claimed something reports what was removed."""
    monkeypatch.setattr(reg, "manifest", lambda: _DEMO)
    lines = reg.unregister()
    assert lines == ["demo: registration removed for md."]
