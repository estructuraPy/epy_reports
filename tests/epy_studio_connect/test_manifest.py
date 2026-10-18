"""The per-app Studio identity."""

from __future__ import annotations

import pytest

from epy_reports.epy_studio_connect import StudioManifest
from epy_reports.epy_studio_connect._manifest import MANIFEST, manifest


def test_the_shipped_manifest() -> None:
    """The shipped identity matches the catalog's own values."""
    entry = manifest()
    assert entry is MANIFEST
    assert entry.app_id == "epy_reports"
    assert entry.display == "ePy Reports"
    assert entry.register == "default"
    assert entry.entry_point == "epy_reports.app"
    assert entry.claims_default is True


def test_the_claim_matches_the_mode() -> None:
    """A 'none' application claims no document type; the rest claim one."""
    entry = manifest()
    if entry.register == "none":
        assert not entry.registers
        assert entry.document_types == ()
    else:
        assert entry.registers
        assert entry.document_types


def test_as_dict_is_json_ready() -> None:
    """The mapping carries the keys Studio's catalog uses."""
    payload = manifest().as_dict()
    expected = ["md", "markdown", "qmd"]
    assert payload["id"] == "epy_reports"
    assert payload["document_types"] == expected


def test_a_register_mode_nobody_handles_is_refused() -> None:
    """A mode outside the closed set would register nothing and say so."""
    with pytest.raises(ValueError, match="register"):
        StudioManifest(
            app_id="x",
            display="X",
            description="d",
            component="c",
            register="broken",
        )


def test_claiming_none_with_document_types_is_refused() -> None:
    """An application that claims nothing must claim no document type."""
    with pytest.raises(ValueError, match="claim"):
        StudioManifest(
            app_id="x",
            display="X",
            description="d",
            component="c",
            register="none",
            document_types=("md",),
        )


def test_a_default_claimant_exposes_both_flags() -> None:
    """The two derived properties agree with the mode."""
    entry = StudioManifest(
        app_id="x",
        display="X",
        description="d",
        component="c",
        register="default",
        document_types=("md",),
    )
    assert entry.registers
    assert entry.claims_default
