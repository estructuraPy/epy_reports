"""epy_reports — Markdown report editor with PDF export.

Single public API for the suite (mirrors ``epy_slides.SlideDeck`` /
``epy_paper.Paper`` / ``epy_project.ProjectManager``)::

    from epy_reports import Report

    report = Report.from_file("report.md", theme="corporate")
    report.to_html("report.html")    # continuous, self-contained web page
    report.to_docx("report.docx")    # Word, with the theme reference doc
    report.to_pdf("report.pdf")      # paginated via Paged.js (needs PySide6)

The GUI application is ``epy_reports.app:main``; the facade below is the
importable, scriptable entry point and pulls in Qt only for ``to_pdf``.
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.6"

__all__ = ["Report", "__version__"]


class Report:
    """One report source that exports to HTML, Word and PDF."""

    def __init__(
        self,
        source: str,
        base_dir: Path | None = None,
        theme: str = "corporate",
    ) -> None:
        """Build a report from Quarto/Markdown ``source``."""
        self.source = source
        self.base_dir = base_dir
        self.theme_id = theme

    @classmethod
    def from_file(
        cls, path: str | Path, theme: str = "corporate"
    ) -> Report:
        """Build a report by reading a Markdown file."""
        p = Path(path)
        return cls(
            p.read_text(encoding="utf-8"), base_dir=p.parent, theme=theme
        )

    def _theme(self):
        """Return the active Theme object."""
        from epy_reports import themes  # noqa: PLC0415

        return themes.get(self.theme_id)

    def _theme_css(self) -> str:
        """Return the document CSS for the active theme."""
        from epy_reports._design import document_css  # noqa: PLC0415

        return document_css(self._theme())

    def to_html(self, path: str | Path, *, continuous: bool = True) -> Path:
        """Write a self-contained HTML page (continuous web document)."""
        from epy_reports.renderer import render_markdown  # noqa: PLC0415

        html = render_markdown(
            self.source,
            base_dir=self.base_dir,
            theme_css=self._theme_css(),
            continuous=continuous,
        )
        out = Path(path)
        out.write_text(html, encoding="utf-8")
        return out

    def _reference_doc(self) -> Path | None:
        """Resolve the bundled Word reference doc for the active theme."""
        from importlib import resources  # noqa: PLC0415

        try:
            anchor = resources.files(
                "epy_reports._config._assets.reference_docx"
            ).joinpath(f"{self.theme_id}.docx")
            with resources.as_file(anchor) as p:
                return Path(p) if Path(p).is_file() else None
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            return None

    def to_docx(self, path: str | Path) -> Path:
        """Write a Word document (Pandoc + the theme reference doc)."""
        from epy_reports.renderer import export_docx  # noqa: PLC0415

        out = Path(path)
        export_docx(
            self.source, out, base_dir=self.base_dir,
            reference_doc=self._reference_doc(), theme_css=self._theme_css(),
        )
        return out

    def to_pdf(self, path: str | Path, *, timeout_ms: int = 60000) -> Path:
        """Write a paginated PDF via Paged.js (needs PySide6)."""
        from epy_reports._export_pdf import render_report_pdf  # noqa: PLC0415

        out = Path(path)
        render_report_pdf(
            self.source,
            out,
            base_dir=self.base_dir,
            theme_css=self._theme_css(),
            page_bg=self._theme().css_vars.get("bg", ""),
            timeout_ms=timeout_ms,
        )
        return out
