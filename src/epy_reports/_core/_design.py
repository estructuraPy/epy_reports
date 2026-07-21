"""Theme-driven design components shared by slides, documents and papers.

A single :func:`design_css` produces the CSS for a small vocabulary of
composition components — lead text, accents, badges, cards, big stats,
timelines and agendas — all derived from the active theme's ``css_vars`` so
the look stays coordinated with the rest of the deck. The ``scope`` selector
prefix lets the same definitions style a reveal.js deck (``".reveal "``) or a
flowing document (``""`` / ``".doc-content "``).

:func:`design_block` returns the authoring skeleton for each component, so the
three sibling apps (slides, reports, paper) expose exactly the same insert
options from one source of truth — only the output format differs.

Markup vocabulary (Pandoc fenced divs / bracketed spans):

* ``::: {.card} … :::`` — a bordered card; group several in ``::: {.cards}``.
* ``::: {.stat}`` with ``**NUMBER**`` then a label — a big number with a
  caption; group several in ``::: {.stats}``.
* ``[text]{.badge}`` — a pill badge.
* ``::: {.timeline}`` over a bullet list — a vertical timeline.
* ``::: {.agenda}`` over a list — a numbered agenda.
* ``::: {.verdict .pass|.fail|.warn}`` — a headline PASS/FAIL/WARN banner.
* ``::: {.checklist}`` over a task list — a review punch-list.
* ``[text]{.badge .pass|.fail|.warn}`` — a status pill.
* ``[text]{.lead}`` / ``[text]{.muted}`` — emphasised / dimmed text.
"""

from __future__ import annotations

from epy_reports._ui.themes_base import Theme

__all__ = [
    "DESIGN_BLOCKS",
    "DESIGN_BLOCK_LABELS",
    "DISCLOSURE_PRESETS",
    "DISCLOSURE_KINDS",
    "design_block",
    "disclosure_block",
    "design_css",
    "document_css",
]


def _v(theme: Theme, key: str, default: str = "") -> str:
    """Return a css var from *theme*, falling back to *default*."""
    return theme.css_vars.get(key, default)


def document_css(theme: Theme) -> str:
    """Theme ``:root`` vars + ``--epy-*`` aliases + component CSS.

    Used as the document's theme stylesheet so flowing documents pick up
    the same design components as the slide decks, and the diagram engines
    (which read ``--epy-*``) inherit the document palette.
    """
    return (
        theme.to_css()
        + "\n:root {"
        " --epy-primary: var(--link);"
        " --epy-fg: var(--fg);"
        " --epy-bg: var(--bg);"
        " --epy-soft: var(--bg-soft);"
        " --epy-border: var(--border);"
        " --epy-pass: var(--callout-tip-border);"
        " --epy-fail: var(--callout-caution-border);"
        " --epy-warn: var(--callout-warning-border);"
        " }\n"
        + design_css(theme, scope="")
    )


def design_css(theme: Theme, *, scope: str = "") -> str:
    """Return theme-driven component CSS, every selector prefixed by ``scope``.

    Args:
        theme: The active visual theme; colours and fonts come from its
            ``css_vars``.
        scope: Selector prefix, e.g. ``".reveal "`` for a deck or ``""`` for a
            document, so the same components style both targets.
    """
    bg = _v(theme, "bg", "#ffffff")
    fg = _v(theme, "fg", "#222222")
    heading = _v(theme, "heading-color", fg)
    primary = _v(theme, "link", "#2a76dd")
    border = _v(theme, "border", "#d0d0d0")
    soft = _v(theme, "bg-soft", _v(theme, "code-bg", "#f3f3f3"))
    font_head = _v(theme, "font-family-headings", "inherit")
    pass_color = _v(theme, "callout-tip-border", "#1a7f37")
    pass_bg = _v(theme, "callout-tip-bg", "#dafbe1")
    fail_color = _v(theme, "callout-caution-border", "#d1242f")
    fail_bg = _v(theme, "callout-caution-bg", "#ffebe9")
    warn_color = _v(theme, "callout-warning-border", "#bf8700")
    warn_bg = _v(theme, "callout-warning-bg", "#fff8c5")
    s = scope
    return f"""
/* lead / accents */
{s}.lead {{ font-size: 1.15em; opacity: 0.9; }}
{s}.muted {{ opacity: 0.65; }}
{s}.accent {{ color: {primary}; }}
{s}.accent-bar, {s}hr.accent-bar {{
  height: 0.18em; width: 2.4em; border: none; border-radius: 2px;
  background: {primary}; margin: 0.35em 0;
}}
{s}.badge {{
  display: inline-block; padding: 0.08em 0.55em; border-radius: 999px;
  background: {primary}; color: {bg}; font-size: 0.62em; font-weight: 700;
  vertical-align: middle; font-family: {font_head};
}}

/* cards */
{s}.cards {{
  display: grid; gap: 0.7em; align-items: stretch;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
}}
{s}.card {{
  background: {soft}; border: 1px solid {border};
  border-top: 4px solid {primary}; border-radius: 10px;
  padding: 0.55em 0.8em; text-align: left;
}}
{s}.card > :first-child {{ margin-top: 0; }}
{s}.card > :last-child {{ margin-bottom: 0; }}
{s}.card h1, {s}.card h2, {s}.card h3,
{s}.card h4, {s}.card h5 {{ color: {heading}; }}

/* big stats */
{s}.stats {{
  display: grid; gap: 1em; align-items: end; width: 100%;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
}}
{s}.stat {{ text-align: center; min-width: 0; }}
{s}.stat p {{ margin: 0.1em 0; }}
{s}.stat strong {{
  display: block; font-size: 2.2em; font-weight: 800; line-height: 1;
  color: {primary}; font-family: {font_head}; white-space: nowrap;
}}
{s}.stat .stat-label {{ display: block; font-size: 0.68em; opacity: 0.8; }}
/* shrink the figures as more stats share the row so they keep fitting */
{s}.stats:has(.stat:nth-child(4)) .stat strong {{ font-size: 1.8em; }}
{s}.stats:has(.stat:nth-child(5)) .stat strong {{ font-size: 1.5em; }}

/* timeline */
{s}.timeline ul {{
  list-style: none; margin: 0.3em 0; padding-left: 1.2em;
  border-left: 3px solid {primary};
}}
{s}.timeline li {{
  position: relative; margin: 0 0 0.55em; padding-left: 0.4em;
}}
{s}.timeline li::before {{
  content: ""; position: absolute; left: -1.58em; top: 0.32em;
  width: 0.62em; height: 0.62em; border-radius: 50%;
  background: {primary}; box-shadow: 0 0 0 3px {bg};
}}

/* agenda */
{s}.agenda ul {{ list-style: none; counter-reset: agenda; padding-left: 0; }}
{s}.agenda li {{
  counter-increment: agenda; position: relative;
  padding-left: 1.8em; margin: 0.4em 0;
}}
{s}.agenda li::before {{
  content: counter(agenda); position: absolute; left: 0; top: 0.05em;
  width: 1.25em; height: 1.25em; line-height: 1.25em; text-align: center;
  border-radius: 50%; background: {primary}; color: {bg};
  font-size: 0.7em; font-weight: 700; font-family: {font_head};
}}

/* status pills — override the base badge's accent background */
{s}.badge.pass {{ background: {pass_color}; }}
{s}.badge.fail {{ background: {fail_color}; }}
{s}.badge.warn {{ background: {warn_color}; }}

/* verdict — a headline banner stating a PASS/FAIL/WARN outcome */
{s}.verdict {{
  display: flex; align-items: center; gap: 0.6em;
  padding: 0.7em 1em; margin: 1em 0; border-radius: 8px;
  border-left: 4px solid {border}; background: {soft};
  font-weight: 700; font-family: {font_head};
}}
{s}.verdict > :first-child {{ margin-top: 0; }}
{s}.verdict > :last-child {{ margin-bottom: 0; }}
{s}.verdict.pass {{
  border-left-color: {pass_color}; background: {pass_bg}; color: {pass_color};
}}
{s}.verdict.fail {{
  border-left-color: {fail_color}; background: {fail_bg}; color: {fail_color};
}}
{s}.verdict.warn {{
  border-left-color: {warn_color}; background: {warn_bg}; color: {warn_color};
}}

/* checklist — a task list styled as a review punch list */
{s}.checklist ul.task-list,
{s}.checklist ul[class~="task-list"] {{
  list-style: none; padding-left: 0; margin: 0.5em 0;
}}
{s}.checklist li {{
  padding: 0.35em 0.2em 0.35em 1.9em; position: relative;
  border-bottom: 1px solid {border};
}}
{s}.checklist li:last-child {{ border-bottom: none; }}
{s}.checklist input[type="checkbox"] {{
  position: absolute; left: 0.1em; top: 0.62em; transform: scale(1.15);
  accent-color: {primary};
}}

/* disclosure — a quiet, insertable note (e.g. an AI-use disclosure) */
{s}.disclosure {{
  margin: 0.8em 0; padding: 0.5em 0.85em;
  border-left: 3px solid {border}; border-radius: 6px;
  background: {soft}; color: {fg}; font-size: 0.82em; opacity: 0.85;
}}
{s}.disclosure > :first-child {{ margin-top: 0; }}
{s}.disclosure > :last-child {{ margin-bottom: 0; }}
"""


# --- authoring skeletons --------------------------------------------------
# The same insert options are exposed by all three sibling apps; only the
# output format (reveal.js / flowing document / journal manuscript) differs.

DESIGN_BLOCKS: tuple[str, ...] = (
    "lead",
    "badge",
    "card",
    "cards",
    "stat",
    "stats",
    "timeline",
    "agenda",
    "verdict",
    "checklist",
)

DESIGN_BLOCK_LABELS: dict[str, str] = {
    "lead": "Lead text",
    "badge": "Badge",
    "card": "Card",
    "cards": "Cards (grid)",
    "stat": "Big stat",
    "stats": "Big stats (row)",
    "timeline": "Timeline",
    "agenda": "Agenda",
    "verdict": "Verdict banner",
    "checklist": "Checklist",
}

_BLOCK_SKELETONS: dict[str, str] = {
    "lead": "\n[Lead sentence that frames the section.]{.lead}\n",
    "badge": "\n[NEW]{.badge}\n",
    "card": (
        "\n::: {.card}\n"
        "### Card title\n\n"
        "Card body text.\n"
        ":::\n"
    ),
    "cards": (
        "\n::::: {.cards}\n"
        ":::: {.card}\n"
        "### First\n\n"
        "Body text.\n"
        "::::\n"
        ":::: {.card}\n"
        "### Second\n\n"
        "Body text.\n"
        "::::\n"
        ":::: {.card}\n"
        "### Third\n\n"
        "Body text.\n"
        "::::\n"
        ":::::\n"
    ),
    "stat": (
        "\n::: {.stat}\n"
        "**42**\n\n"
        "[Metric label]{.stat-label}\n"
        ":::\n"
    ),
    "stats": (
        "\n::::: {.stats}\n"
        ":::: {.stat}\n"
        "**42**\n\n"
        "[First metric]{.stat-label}\n"
        "::::\n"
        ":::: {.stat}\n"
        "**7×**\n\n"
        "[Second metric]{.stat-label}\n"
        "::::\n"
        ":::: {.stat}\n"
        "**99%**\n\n"
        "[Third metric]{.stat-label}\n"
        "::::\n"
        ":::::\n"
    ),
    "timeline": (
        "\n::: {.timeline}\n"
        "- **2024** — First milestone.\n"
        "- **2025** — Second milestone.\n"
        "- **2026** — Third milestone.\n"
        ":::\n"
    ),
    "agenda": (
        "\n::: {.agenda}\n"
        "- First item\n"
        "- Second item\n"
        "- Third item\n"
        ":::\n"
    ),
    "verdict": (
        "\n::: {.verdict .pass}\n"
        "**PASS** — All checks within tolerance.\n"
        ":::\n"
    ),
    "checklist": (
        "\n::: {.checklist}\n"
        "- [x] First item verified\n"
        "- [x] Second item verified\n"
        "- [ ] Third item pending\n"
        ":::\n"
    ),
}

_BLOCK_TOKENS: dict[str, str] = {
    "lead": "Lead sentence that frames the section.",
    "badge": "NEW",
    "card": "Card title",
    "cards": "First",
    "stat": "42",
    "stats": "42",
    "timeline": "First milestone.",
    "agenda": "First item",
    "verdict": "All checks within tolerance.",
    "checklist": "First item verified",
}


def design_block(kind: str) -> tuple[str, str]:
    """Return ``(markdown_skeleton, select_token)`` for a design block.

    The skeleton uses Pandoc fenced-div / bracketed-span syntax so the same
    source renders in a reveal.js deck, a flowing document and a journal
    manuscript. ``select_token`` is the substring an editor should pre-select
    so the user can immediately type over the placeholder.
    """
    skeleton = _BLOCK_SKELETONS.get(kind, _BLOCK_SKELETONS["card"])
    token = _BLOCK_TOKENS.get(kind, "")
    return skeleton, token


# --- disclosures ----------------------------------------------------------
# A disclosure is an insertable, theme-styled note (see the ``.disclosure``
# CSS in :func:`design_css`) that states a condition of use. It is NOT tied to
# AI: the presets below cover the common cases — AI assistance, document
# integrity, confidentiality and draft status — and the inserted text is fully
# editable, so any wording can replace a preset. All three sibling apps expose
# the same set from this one source of truth (only the output format differs).

DISCLOSURE_PRESETS: dict[str, tuple[str, str]] = {
    "ai": (
        "AI assistance",
        "This document was prepared with the assistance of AI; review its "
        "content before relying on it.",
    ),
    "integrity": (
        "Document integrity",
        "This document is valid only when used in its entirety; partial "
        "reproduction or extraction may misrepresent its content.",
    ),
    "confidential": (
        "Confidentiality",
        "Confidential — intended solely for the named recipient; do not "
        "distribute without authorization.",
    ),
    "draft": (
        "Draft",
        "Draft — provisional content, not for distribution and subject to "
        "change.",
    ),
}

DISCLOSURE_KINDS: tuple[str, ...] = tuple(DISCLOSURE_PRESETS)


def disclosure_block(kind: str = "ai") -> tuple[str, str]:
    """Return ``(markdown_skeleton, select_token)`` for a disclosure preset.

    The skeleton wraps the preset text in a ``::: {.disclosure}`` fenced div so
    it renders as a quiet, theme-styled note in every app. ``select_token`` is
    the body text an editor should pre-select so the user can immediately type
    over it. Unknown kinds fall back to the AI-use disclosure.
    """
    _, text = DISCLOSURE_PRESETS.get(kind, DISCLOSURE_PRESETS["ai"])
    skeleton = f"\n::: {{.disclosure}}\n{text}\n:::\n"
    return skeleton, text
