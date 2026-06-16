"""Tests for the bundled-CSL resolver in renderer.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from epy_mdr.renderer import (
    CSL_STYLES,
    DEFAULT_CSL_STYLE,
    _bibliography_args,
    _resolve_csl,
)


def test_default_resolves_to_ieee():
    path = _resolve_csl(None, None)
    assert path is not None
    assert path.name == "ieee.csl"


def test_empty_string_resolves_to_ieee():
    path = _resolve_csl("", None)
    assert path is not None
    assert path.name == "ieee.csl"


@pytest.mark.parametrize("key,expected", [
    ("ieee", "ieee.csl"),
    ("apa", "apa.csl"),
    ("chicago", "chicago-author-date.csl"),
])
def test_short_names_resolve_to_bundled(key, expected):
    path = _resolve_csl(key, None)
    assert path is not None
    assert path.name == expected


def test_short_name_is_case_insensitive():
    assert _resolve_csl("IEEE", None) == _resolve_csl("ieee", None)
    assert _resolve_csl("Apa", None) == _resolve_csl("apa", None)


def test_unknown_short_name_falls_through_to_path():
    # Not a known key and not an existing path → None (caller skips --csl)
    assert _resolve_csl("unknown-style", None) is None


def test_custom_path_resolves_when_present(tmp_path: Path):
    custom = tmp_path / "custom.csl"
    custom.write_text("<style/>", encoding="utf-8")
    path = _resolve_csl(str(custom), tmp_path)
    assert path is not None
    assert path.resolve() == custom.resolve()


def test_relative_path_resolves_against_base_dir(tmp_path: Path):
    custom = tmp_path / "local.csl"
    custom.write_text("<style/>", encoding="utf-8")
    path = _resolve_csl("local.csl", tmp_path)
    assert path is not None
    assert path.name == "local.csl"


def test_three_styles_registered():
    assert set(CSL_STYLES) == {"ieee", "apa", "chicago"}


def test_default_is_ieee():
    assert DEFAULT_CSL_STYLE == "ieee"


def test_bibliography_args_inject_default_csl(tmp_path: Path):
    bib = tmp_path / "refs.bib"
    bib.write_text("@misc{a, title={t}}\n", encoding="utf-8")
    args = _bibliography_args({"bibliography": "refs.bib"}, tmp_path)
    assert "--citeproc" in args
    csl_args = [a for a in args if a.startswith("--csl=")]
    assert csl_args, "default IEEE CSL must be injected when bib is set"
    assert csl_args[0].endswith("ieee.csl")


def test_bibliography_args_respect_yaml_csl(tmp_path: Path):
    bib = tmp_path / "refs.bib"
    bib.write_text("@misc{a, title={t}}\n", encoding="utf-8")
    args = _bibliography_args(
        {"bibliography": "refs.bib", "csl": "apa"}, tmp_path
    )
    csl_args = [a for a in args if a.startswith("--csl=")]
    assert csl_args and csl_args[0].endswith("apa.csl")


def test_no_bibliography_no_args(tmp_path: Path):
    assert _bibliography_args({}, tmp_path) == []
