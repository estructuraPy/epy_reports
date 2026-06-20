"""Diagram fenced-block handling shared by the preview and exports.

Converts ```mermaid and ```nomnoml fenced code blocks into raw-HTML
``<pre>`` placeholders that the bundled browser engines render at load
time, and reports which engines a document uses so only the needed
bundles are injected.
"""

from __future__ import annotations

import re

_MERMAID_FENCE_RE = re.compile(
    r"^[ \t]*`{3,}[ \t]*\{?\.?mermaid[^\n}]*\}?[ \t]*\n(?P<body>.*?)\n"
    r"[ \t]*`{3,}[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
_NOMNOML_FENCE_RE = re.compile(
    r"^[ \t]*`{3,}[ \t]*\{?\.?nomnoml[^\n}]*\}?[ \t]*\n(?P<body>.*?)\n"
    r"[ \t]*`{3,}[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


def _diagram_pre(body: str, cls: str) -> str:
    """Wrap a diagram definition in a raw-HTML ``<pre>`` of class *cls*."""
    esc = (
        body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return f'\n```{{=html}}\n<pre class="{cls}">\n{esc}\n</pre>\n```\n'


def expand_diagrams(source: str) -> str:
    """Convert ```mermaid / ```nomnoml fences to raw-HTML placeholders."""
    source = _MERMAID_FENCE_RE.sub(
        lambda m: _diagram_pre(m.group("body"), "mermaid"), source
    )
    return _NOMNOML_FENCE_RE.sub(
        lambda m: _diagram_pre(m.group("body"), "nomnoml"), source
    )


def diagram_engines(source: str) -> set[str]:
    """Return the diagram engines used in *source* (mermaid / nomnoml)."""
    engines: set[str] = set()
    if _MERMAID_FENCE_RE.search(source):
        engines.add("mermaid")
    if _NOMNOML_FENCE_RE.search(source):
        engines.add("nomnoml")
    return engines
