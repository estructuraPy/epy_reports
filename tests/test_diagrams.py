"""Tests for the mermaid/nomnoml fenced-block expansion helpers."""

from __future__ import annotations

from epy_reports._diagrams import diagram_engines, expand_diagrams

_MERMAID = "```mermaid\nflowchart LR\nA-->B\n```\n"
_NOMNOML = "```nomnoml\n[A] -> [B]\n```\n"


def test_expand_mermaid_to_raw_html():
    """A mermaid fence becomes a raw-HTML pre.mermaid placeholder."""
    out = expand_diagrams(_MERMAID)
    assert '<pre class="mermaid">' in out
    assert "{=html}" in out
    assert "flowchart LR" in out


def test_expand_nomnoml_to_raw_html():
    """A nomnoml fence becomes a raw-HTML pre.nomnoml placeholder."""
    out = expand_diagrams(_NOMNOML)
    assert '<pre class="nomnoml">' in out


def test_expand_escapes_html_special_chars():
    """Angle brackets / ampersands in the body are HTML-escaped."""
    src = "```mermaid\nA & <B>\n```\n"
    out = expand_diagrams(src)
    assert "&amp;" in out
    assert "&lt;B&gt;" in out


def test_expand_leaves_plain_code_untouched():
    """A plain ```python fence is not treated as a diagram."""
    src = "```python\nprint('hi')\n```\n"
    assert expand_diagrams(src) == src


def test_diagram_engines_detects_both():
    """Both engines are reported when both fences are present."""
    engines = diagram_engines(_MERMAID + "\n" + _NOMNOML)
    assert engines == {"mermaid", "nomnoml"}


def test_diagram_engines_empty_for_plain_text():
    """A document with no diagrams reports no engines."""
    assert diagram_engines("# Heading\n\nBody text.\n") == set()
