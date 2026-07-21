"""Tests for the config-template persistence module."""

from __future__ import annotations

import pytest

from epy_reports._core import templates


@pytest.fixture
def base_dir(tmp_path):
    """Provide a temporary templates directory."""
    return tmp_path / "templates"


def test_save_list_load_delete_roundtrip(base_dir):
    data = {
        "theme": "corporate",
        "csl": "ieee",
        "footer": "ANM Ingeniería",
        "page_numbers": "true",
        "cover": "false",
        "logo": "",
    }
    templates.save_template("My Style", data, base_dir=base_dir)
    assert templates.list_templates(base_dir=base_dir) == ["My Style"]

    loaded = templates.load_template("My Style", base_dir=base_dir)
    assert loaded == data

    templates.delete_template("My Style", base_dir=base_dir)
    assert templates.list_templates(base_dir=base_dir) == []


def test_on_disk_json_is_single_line(base_dir):
    data = {"theme": "x", "csl": "apa", "footer": "f", "cover": "true"}
    templates.save_template("compact", data, base_dir=base_dir)
    path = base_dir / "compact.json"
    content = path.read_text(encoding="utf-8")
    # The leaf object must be a single line (no newline inside).
    assert "\n" not in content.strip()


def test_list_empty_when_dir_absent(base_dir):
    assert templates.list_templates(base_dir=base_dir) == []


def test_load_missing_raises(base_dir):
    with pytest.raises(FileNotFoundError):
        templates.load_template("nope", base_dir=base_dir)


def test_delete_missing_is_noop(base_dir):
    # Should not raise.
    templates.delete_template("ghost", base_dir=base_dir)


def test_empty_name_rejected(base_dir):
    with pytest.raises(ValueError):
        templates.save_template("///", {"theme": "x"}, base_dir=base_dir)
