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

from epy_reports._core._plotly import figure_to_markdown

__version__ = "0.7.1"

__all__ = [
    "Report",
    "__version__",
    "document_css",
    "figure_to_markdown",
    "get_theme",
    "render_markdown",
]


# Pinning ICU before Qt loads lived here, and identically in
# epy_slides and epy_papers -- two of those copies documenting that
# they mirrored this one. It is epy_export's now. The call stays
# explicit and stays HERE, ahead of anything that touches Qt,
# because the ordering is the whole point and a side effect fired
# from an unrelated import is how it stops being reviewable.
from epy_export import pin_system_icu

pin_system_icu()


from epy_reports._core._report import Report  # noqa: E402

#: Rendering markdown as themed HTML is what other libraries need from
#: epy_reports, and reaching it through _core.themes / _core._design /
#: _core.renderer was the private seam they used. Measured: importing
#: _core.themes pulls in PySide6 (+56 modules) and _core.renderer costs
#: 0.8 s, so binding either at module level would contradict this
#: package's own contract -- Qt loads only for to_pdf, and nothing that
#: touches Qt may precede the ICU pin above. They are therefore published
#: lazily (PEP 562): public names, import cost paid on first use.
#:
#: ``get_theme`` is ``_core.themes.get`` under a name that survives being
#: read at the top level of another library; ``get`` alone does not.
_LAZY = {"get_theme", "document_css", "render_markdown", "renderer"}


def __getattr__(name: str) -> object:
    """Resolve the heavyweight rendering exports on first use."""
    if name in _LAZY:
        if name == "get_theme":
            from epy_reports._core import themes

            return themes.get
        if name == "document_css":
            from epy_reports._core._design import document_css

            return document_css
        if name == "renderer":
            # The module itself, so a sibling can patch its seams (the census
            # forbids reaching the private leaf directly). Lazy for the same
            # reason as render_markdown below: it pulls the Markdown stack in.
            from epy_reports._core import renderer

            return renderer
        from epy_reports._core.renderer import render_markdown

        return render_markdown
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
