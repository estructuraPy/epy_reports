"""Formal API compliance tests for epy_reports.

Verifies that the public exports are importable, have the expected interface,
and conform to the declared __all__ contract.
"""

from __future__ import annotations

import re

import epy_reports as er

# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------


class TestImportability:
    def test_package_importable(self):
        assert er is not None

    def test_report_importable(self):
        from epy_reports import Report

        assert isinstance(Report, type)


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_attribute_exists(self):
        assert hasattr(er, "__version__")

    def test_version_is_string(self):
        assert isinstance(er.__version__, str)

    def test_version_semver_format(self):
        parts = er.__version__.split(".")
        assert len(parts) == 3, f"Expected 3 version parts, got {parts}"

    def test_version_parts_are_numeric(self):
        for part in er.__version__.split("."):
            assert re.match(r"^\d+", part), f"Non-numeric version part: {part!r}"


# ---------------------------------------------------------------------------
# __all__ contract
# ---------------------------------------------------------------------------


class TestAllContract:
    _EXPECTED = ["Report", "__version__"]

    def test_all_exists(self):
        assert hasattr(er, "__all__")

    def test_all_matches_declared_contract(self):
        assert sorted(er.__all__) == sorted(self._EXPECTED)

    def test_all_symbols_importable(self):
        for name in er.__all__:
            assert hasattr(er, name), f"__all__ member {name!r} not found on module"


# ---------------------------------------------------------------------------
# Report facade
# ---------------------------------------------------------------------------


class TestReportMethods:
    _REQUIRED_METHODS = ["to_html", "to_docx", "to_pdf"]
    _REQUIRED_CLASSMETHODS = ["from_file"]

    def test_required_methods_present(self):
        from epy_reports import Report

        for method in self._REQUIRED_METHODS:
            assert hasattr(Report, method), f"Report missing: {method!r}"

    def test_required_methods_callable(self):
        from epy_reports import Report

        for method in self._REQUIRED_METHODS:
            assert callable(getattr(Report, method)), f"{method!r} is not callable"

    def test_required_classmethods_present(self):
        from epy_reports import Report

        for method in self._REQUIRED_CLASSMETHODS:
            assert callable(getattr(Report, method)), f"Report.{method!r} is not callable"


class TestReportInit:
    def test_default_theme_is_corporate(self):
        from epy_reports import Report

        r = Report("# Title\n\nBody")
        assert r.theme_id == "corporate"

    def test_custom_theme_stored(self):
        from epy_reports import Report

        r = Report("# Title\n\nBody", theme="minimal")
        assert r.theme_id == "minimal"

    def test_source_stored(self):
        from epy_reports import Report

        r = Report("# Title\n\nBody")
        assert r.source == "# Title\n\nBody"

    def test_from_file_reads_content(self, tmp_path):
        from epy_reports import Report

        md_file = tmp_path / "sample.md"
        md_file.write_text("# Title\n\nBody", encoding="utf-8")
        r = Report.from_file(md_file)
        assert r.source == "# Title\n\nBody"
        assert r.base_dir == md_file.parent
