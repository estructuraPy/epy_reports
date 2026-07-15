"""Theme dataclass shared between the theme catalogue and its loader."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """A named visual theme covering both the Qt chrome and the HTML.

    Attributes:
        id: Stable identifier persisted in ``QSettings``.
        display_name: Label shown in the Theme menu.
        qt_palette: ``QPalette.ColorRole`` name → hex color.
        css_vars: ``--name`` (without dashes) → CSS value.
    """

    id: str
    display_name: str
    qt_palette: dict[str, str]
    css_vars: dict[str, str]

    def to_css(self) -> str:
        """Serialise ``css_vars`` as a ``:root { … }`` block."""
        if not self.css_vars:
            return ""
        lines = [":root {"]
        for name, value in self.css_vars.items():
            lines.append(f"    --{name}: {value};")
        lines.append("}")
        return "\n".join(lines)
