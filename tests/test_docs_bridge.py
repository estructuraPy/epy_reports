"""Tests for epy_reports.epy_suite_connect.docs_bridge (pure Python, no Qt required)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Availability detection
# ---------------------------------------------------------------------------


def test_epy_docs_available_true():
    """Returns True when find_spec finds epy_docs."""
    from epy_reports.epy_suite_connect.docs_bridge import epy_docs_available

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.importlib.util.find_spec",
        return_value=MagicMock(),
    ):
        assert epy_docs_available() is True


def test_epy_docs_available_false():
    """Returns False when find_spec returns None (package absent)."""
    from epy_reports.epy_suite_connect.docs_bridge import epy_docs_available

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.importlib.util.find_spec",
        return_value=None,
    ):
        assert epy_docs_available() is False


# ---------------------------------------------------------------------------
# list_layouts / list_document_types — delegate to epy_docs (installed)
# ---------------------------------------------------------------------------


def test_list_layouts_returns_real_values():
    """list_layouts() delegates to epy_docs.available_layouts()."""
    from epy_reports.epy_suite_connect.docs_bridge import list_layouts

    layouts = list_layouts()
    assert isinstance(layouts, list)
    assert len(layouts) > 0
    assert "corporate" in layouts


def test_list_document_types_returns_real_values():
    """list_document_types() delegates to available_document_types()."""
    from epy_reports.epy_suite_connect.docs_bridge import list_document_types

    doc_types = list_document_types()
    assert isinstance(doc_types, list)
    assert len(doc_types) > 0
    assert "report" in doc_types


# ---------------------------------------------------------------------------
# list_* — error path when epy_docs is absent
# ---------------------------------------------------------------------------


def test_list_layouts_raises_when_unavailable():
    """list_layouts() raises BridgeUnavailableError if epy_docs missing."""
    from epy_reports.epy_suite_connect.docs_bridge import BridgeUnavailableError, list_layouts

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.importlib.util.find_spec",
        return_value=None,
    ):
        try:
            list_layouts()
        except BridgeUnavailableError:
            pass
        else:
            raise AssertionError("Expected BridgeUnavailableError")


def test_list_document_types_raises_when_unavailable():
    """list_document_types() raises BridgeUnavailableError when absent."""
    from epy_reports.epy_suite_connect.docs_bridge import (
        BridgeUnavailableError,
        list_document_types,
    )

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.importlib.util.find_spec",
        return_value=None,
    ):
        try:
            list_document_types()
        except BridgeUnavailableError:
            pass
        else:
            raise AssertionError("Expected BridgeUnavailableError")


# ---------------------------------------------------------------------------
# render_document — wiring with a mocked DocumentWriter
# ---------------------------------------------------------------------------


def test_render_document_calls_writer_correctly():
    """render_document passes the right args to DocumentWriter."""
    fake_result = {"status": "ok"}
    mock_writer = MagicMock()
    mock_writer.generate.return_value = fake_result

    mock_writer_cls = MagicMock(return_value=mock_writer)

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.epy_docs_available", return_value=True
    ):
        import sys

        fake_epy_docs = MagicMock()
        fake_epy_docs.DocumentWriter = mock_writer_cls

        with patch.dict(sys.modules, {"epy_docs": fake_epy_docs}):
            from epy_reports.epy_suite_connect.docs_bridge import render_document

            source = Path("/tmp/my_report.qmd")
            out_dir = Path("/tmp/results")

            result = render_document(
                source_path=source,
                layout="corporate",
                document_type="report",
                output_dir=out_dir,
                pdf=True,
                html=False,
            )

    # DocumentWriter constructor
    mock_writer_cls.assert_called_once_with(
        "report",
        layout_style="corporate",
        output_dir=str(out_dir),
        keep_lists_together=True,
    )
    # add_quarto_file
    mock_writer.add_quarto_file.assert_called_once_with(
        str(source),
        convert_tables=False,
        execute_code_blocks=False,
    )
    # generate
    mock_writer.generate.assert_called_once_with(
        output_filename="my_report",
        pdf=True,
        html=False,
        docx=False,
    )
    assert result is fake_result


def test_render_document_html_only():
    """render_document forwards pdf=False, html=True correctly."""
    mock_writer = MagicMock()
    mock_writer.generate.return_value = {}
    mock_writer_cls = MagicMock(return_value=mock_writer)

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.epy_docs_available", return_value=True
    ):
        import sys

        fake_epy_docs = MagicMock()
        fake_epy_docs.DocumentWriter = mock_writer_cls

        with patch.dict(sys.modules, {"epy_docs": fake_epy_docs}):
            from epy_reports.epy_suite_connect.docs_bridge import render_document

            render_document(
                source_path=Path("/tmp/doc.md"),
                layout="minimal",
                document_type="notebook",
                output_dir=Path("/tmp/out"),
                pdf=False,
                html=True,
            )

    mock_writer.generate.assert_called_once_with(
        output_filename="doc",
        pdf=False,
        html=True,
        docx=False,
    )


def test_render_document_docx():
    """render_document forwards docx=True to generate()."""
    mock_writer = MagicMock()
    mock_writer.generate.return_value = {}
    mock_writer_cls = MagicMock(return_value=mock_writer)

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.epy_docs_available", return_value=True
    ):
        import sys

        fake_epy_docs = MagicMock()
        fake_epy_docs.DocumentWriter = mock_writer_cls

        with patch.dict(sys.modules, {"epy_docs": fake_epy_docs}):
            from epy_reports.epy_suite_connect.docs_bridge import render_document

            render_document(
                source_path=Path("/tmp/doc.md"),
                layout="classic",
                document_type="report",
                output_dir=Path("/tmp/out"),
                pdf=False,
                html=False,
                docx=True,
            )

    mock_writer.generate.assert_called_once_with(
        output_filename="doc",
        pdf=False,
        html=False,
        docx=True,
    )


def test_render_document_keep_lists_together_opt_out():
    """render_document forwards keep_lists_together=False to the writer."""
    mock_writer = MagicMock()
    mock_writer.generate.return_value = {}
    mock_writer_cls = MagicMock(return_value=mock_writer)

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.epy_docs_available", return_value=True
    ):
        import sys

        fake_epy_docs = MagicMock()
        fake_epy_docs.DocumentWriter = mock_writer_cls

        with patch.dict(sys.modules, {"epy_docs": fake_epy_docs}):
            from epy_reports.epy_suite_connect.docs_bridge import render_document

            render_document(
                source_path=Path("/tmp/doc.md"),
                layout="classic",
                document_type="report",
                output_dir=Path("/tmp/out"),
                pdf=True,
                html=False,
                keep_lists_together=False,
            )

    mock_writer_cls.assert_called_once_with(
        "report",
        layout_style="classic",
        output_dir=str(Path("/tmp/out")),
        keep_lists_together=False,
    )


# ---------------------------------------------------------------------------
# render_document — error path when epy_docs absent
# ---------------------------------------------------------------------------


def test_render_document_raises_when_unavailable():
    """render_document raises BridgeUnavailableError if epy_docs missing."""
    from epy_reports.epy_suite_connect.docs_bridge import (
        BridgeUnavailableError,
        render_document,
    )

    with patch(
        "epy_reports.epy_suite_connect.docs_bridge.importlib.util.find_spec",
        return_value=None,
    ):
        try:
            render_document(
                source_path=Path("/tmp/x.md"),
                layout="corporate",
                document_type="report",
                output_dir=Path("/tmp/out"),
                pdf=True,
                html=True,
            )
        except BridgeUnavailableError:
            pass
        else:
            raise AssertionError("Expected BridgeUnavailableError")
