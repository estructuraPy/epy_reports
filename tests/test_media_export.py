"""Tests for the DOCX component simplification (no Qt required)."""

from __future__ import annotations

from epy_reports._media_export import (
    collect_diagrams,
    simplify_components_for_export,
    substitute_diagram_images,
)

STATS = """\
:::: {.stats}
::: {.stat}
**28 MPa**

[concrete]{.stat-label}
:::
::: {.stat}
**420 MPa**

[steel]{.stat-label}
:::
::::
"""


def test_stats_become_a_pipe_table():
    out = simplify_components_for_export(STATS)
    assert "| **28 MPa** | **420 MPa** |" in out
    assert "| concrete | steel |" in out
    assert "{.stat}" not in out


def test_cards_become_bold_titled_blocks():
    src = (
        ":::: {.cards}\n::: {.card}\n#### Strength\nText.\n:::\n"
        "::: {.card}\n#### Stiffness\nMore.\n:::\n::::\n"
    )
    out = simplify_components_for_export(src)
    assert "**Strength**" in out
    assert "#### Strength" not in out
    assert "{.card}" not in out


def test_callouts_are_preserved():
    src = '::: {.callout-note title="Keep"}\nBody.\n:::\n'
    out = simplify_components_for_export(src)
    assert ".callout-note" in out


def test_collect_diagrams_in_order():
    src = (
        "```mermaid\nflowchart LR\nA-->B\n```\n\n"
        "```nomnoml\n[A] -> [B]\n```\n"
    )
    engines = [e for e, _ in collect_diagrams(src)]
    assert engines == ["mermaid", "nomnoml"]


def test_substitute_diagram_images_replaces_only_rendered():
    from pathlib import Path

    src = (
        "```mermaid\nflowchart LR\nA-->B\n```\n\n"
        "```nomnoml\n[A] -> [B]\n```\n"
    )
    out = substitute_diagram_images(src, [Path("d0.png"), None])
    assert "![](d0.png)" in out
    # The second diagram had no PNG, so its fence is left intact.
    assert "```nomnoml" in out
