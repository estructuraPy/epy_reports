"""About dialog for epy_mdr.

Displays application version, description, author contact, and the two
organisation logos (ANM Ingenieria + estructuraPy).
"""

from __future__ import annotations

import importlib.resources

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import epy_mdr
from epy_mdr import _i18n as i18n


def _load_branding_pixmap(name: str) -> QPixmap:
    """Load a branding image by filename and return a QPixmap.

    Reads bytes via ``importlib.resources`` so the image is accessible
    both from a source install and from a frozen (zip-backed) build.

    Args:
        name: Filename inside ``epy_mdr.assets.branding``,
            e.g. ``"epy_mdr.png"``.

    Returns:
        A :class:`~PySide6.QtGui.QPixmap` loaded from the embedded bytes,
        or an empty ``QPixmap`` when the resource cannot be found.
    """
    try:
        pkg = importlib.resources.files("epy_mdr.assets.branding")
        data = (pkg / name).read_bytes()
    except (FileNotFoundError, TypeError, ModuleNotFoundError):
        return QPixmap()
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    return pixmap


class AboutDialog(QDialog):
    """Modal 'About epy_mdr' dialog.

    Layout (top to bottom):
        * Application logo scaled to ~180 px wide, centered.
        * App name + version label.
        * One-line description.
        * Horizontal separator.
        * Author block: name (bold), mailto link, org/copyright line.
        * Horizontal row with the two org logos side by side.
        * Standard Close button.

    The dialog inherits the active application stylesheet — no colours
    are hardcoded here.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the dialog and build its layout."""
        super().__init__(parent)
        self.setWindowTitle("About epy_mdr")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setSizeGripEnabled(False)
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(24, 20, 24, 16)

        # --- App logo ---
        logo_pix = _load_branding_pixmap("epy_mdr.png")
        if not logo_pix.isNull():
            logo_pix = logo_pix.scaledToWidth(
                180, Qt.TransformationMode.SmoothTransformation
            )
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        if not logo_pix.isNull():
            logo_lbl.setPixmap(logo_pix)
        root.addWidget(logo_lbl)

        # --- App name + version ---
        name_lbl = QLabel(
            f"<b>epy_mdr</b> &nbsp; v{epy_mdr.__version__}"
        )
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(name_lbl)

        # --- Description ---
        desc_lbl = QLabel(
            "Quarto / Markdown editor with live preview"
        )
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(desc_lbl)

        # --- Separator ---
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        sep.setObjectName("AboutSeparator")
        # A thin line via stylesheet; inherits theme-appropriate colour.
        sep.setStyleSheet(
            "background: palette(mid);"
        )
        root.addWidget(sep)

        # --- Author block ---
        author_name_lbl = QLabel("<b>Ing. Angel Navarro-Mora M.Sc.</b>")
        author_name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(author_name_lbl)

        email_lbl = QLabel(
            '<a href="mailto:ahnavarro@anmingenieria.com">'
            "ahnavarro@anmingenieria.com</a>"
        )
        email_lbl.setOpenExternalLinks(True)
        email_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(email_lbl)

        linkedin_lbl = QLabel(
            '<a href="https://www.linkedin.com/in/ahnavarro">'
            "linkedin.com/in/ahnavarro</a>"
        )
        linkedin_lbl.setOpenExternalLinks(True)
        linkedin_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(linkedin_lbl)

        org_lbl = QLabel(
            '<a href="https://www.anmingenieria.com/">'
            "ANM Ingeniería</a> / estructuraPy © 2026, Costa Rica"
        )
        org_lbl.setOpenExternalLinks(True)
        org_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(org_lbl)

        # --- Org logos row ---
        logos_row = QHBoxLayout()
        logos_row.setSpacing(16)
        logos_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        for filename in ("imagotipo_anm.png", "estructurapy.png"):
            pix = _load_branding_pixmap(filename)
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            if not pix.isNull():
                pix = pix.scaledToWidth(
                    120, Qt.TransformationMode.SmoothTransformation
                )
                lbl.setPixmap(pix)
            logos_row.addWidget(lbl)

        root.addLayout(logos_row)

        # --- Close button ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        i18n.translate_widget(self)
