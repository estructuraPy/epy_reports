"""Bridge module between epy_reports and the optional epy_docs package.

Independence contract
---------------------
This is the **only** module in epy_reports that may reference ``epy_docs``.
All imports of ``epy_docs`` happen lazily inside function bodies so the
rest of the application continues to work when ``epy_docs`` is not
installed.  No top-level ``import epy_docs`` is permitted here or
anywhere else in the package.

Usage example::

    from epy_reports.epy_suite_connect.docs_bridge import (
        epy_docs_available,
        render_document,
    )

    if epy_docs_available():
        result = render_document(
            source_path=Path("report.qmd"),
            layout="corporate",
            document_type="report",
            output_dir=Path("results"),
            pdf=True,
            html=True,
        )
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


class BridgeUnavailableError(RuntimeError):
    """Raised when epy_docs is required but not installed."""


def epy_docs_available() -> bool:
    """Return ``True`` when epy_docs can be imported.

    Returns:
        ``True`` if ``epy_docs`` is findable on ``sys.path``,
        ``False`` otherwise.  No actual import is performed.
    """
    return importlib.util.find_spec("epy_docs") is not None


def list_layouts() -> list[str]:
    """Return the layout names available in epy_docs.

    Returns:
        Sorted list of layout name strings, e.g.
        ``['academic', 'corporate', ...]``.

    Raises:
        BridgeUnavailableError: If epy_docs is not installed.
    """
    if not epy_docs_available():
        raise BridgeUnavailableError(
            "epy_docs is not installed. It is a commercial add-on by "
            "ANM Ingenieria: ahnavarro@anmingenieria.com"
        )
    import epy_docs  # noqa: PLC0415  (lazy import by design)

    return list(epy_docs.available_layouts())


def list_document_types() -> list[str]:
    """Return the document types available in epy_docs.

    Returns:
        Sorted list of document type strings, e.g.
        ``['book', 'notebook', 'paper', 'report']``.

    Raises:
        BridgeUnavailableError: If epy_docs is not installed.
    """
    if not epy_docs_available():
        raise BridgeUnavailableError(
            "epy_docs is not installed. It is a commercial add-on by "
            "ANM Ingenieria: ahnavarro@anmingenieria.com"
        )
    import epy_docs  # noqa: PLC0415

    return list(epy_docs.available_document_types())


def render_document(
    source_path: Path,
    layout: str,
    document_type: str,
    output_dir: Path,
    pdf: bool,
    html: bool,
    docx: bool = False,
    keep_lists_together: bool = True,
) -> dict:
    """Render ``source_path`` through epy_docs and return the result.

    Builds a ``DocumentWriter`` with the given options, adds the source
    file as a Quarto chapter, and calls ``generate()``.

    Args:
        source_path: Absolute path to the ``.md`` or ``.qmd`` source.
        layout: Layout name as returned by :func:`list_layouts`.
        document_type: Document type as returned by
            :func:`list_document_types`.
        output_dir: Directory where epy_docs will write the output
            files.  Created by epy_docs if it does not exist.
        pdf: When ``True``, request PDF output.
        html: When ``True``, request HTML output.
        docx: When ``True``, request Word (.docx) output.
        keep_lists_together: When ``True`` (default), PDF output keeps
            bullet/numbered lists on one page (the whole list moves to
            the next page instead of splitting). Forwarded to
            ``DocumentWriter``; affects PDF only. DOCX output keeps
            lists together unconditionally via the reference templates.

    Returns:
        The ``dict`` returned by ``DocumentWriter.generate()``.

    Raises:
        BridgeUnavailableError: If epy_docs is not installed.
    """
    if not epy_docs_available():
        raise BridgeUnavailableError(
            "epy_docs is not installed. It is a commercial add-on by "
            "ANM Ingenieria: ahnavarro@anmingenieria.com"
        )
    import epy_docs  # noqa: PLC0415

    writer = epy_docs.DocumentWriter(
        document_type,
        layout_style=layout,
        output_dir=str(output_dir),
        keep_lists_together=keep_lists_together,
    )
    writer.add_quarto_file(
        str(source_path),
        convert_tables=False,
        execute_code_blocks=False,
    )
    return writer.generate(
        output_filename=source_path.stem,
        pdf=pdf,
        html=html,
        docx=docx,
    )
