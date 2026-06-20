"""Lightweight in-app internationalization (English / Spanish).

English is the source language and the lookup key; Spanish strings live in
``_ES``. Missing keys fall back to the English text. Widgets register a
relabel callback via :func:`on_language_changed`, so switching the language
re-applies every callback and the running UI updates live, with no restart.

The product name ``epy_mdr``, code identifiers, theme ids, keyboard
shortcuts and citation-style names (IEEE/APA/Chicago) stay in English.
"""

from __future__ import annotations

from collections.abc import Callable

#: Supported languages: code -> endonym shown in the Language menu.
LANGUAGES: dict[str, str] = {"en": "English", "es": "Español"}

_lang = "en"
_observers: list[Callable[[], None]] = []

# English -> Spanish. Neutral / professional Spanish (no regional voseo).
# Keys MUST match the source strings exactly (including the trailing
# "..." vs the "…" ellipsis character and the Qt "&" menu accelerators).
_ES: dict[str, str] = {
    # --- top-level menus (with & accelerator) ---
    "&File": "&Archivo",
    "&Text": "&Texto",
    "&Elements": "&Elementos",
    "&Document": "&Documento",
    "&References": "&Referencias",
    "E&xport": "E&xportar",
    "&View": "&Ver",
    "&Templates": "&Plantillas",
    "&Help": "&Ayuda",
    # --- toolbar dropdown buttons (no accelerator) ---
    "File": "Archivo",
    "Text": "Texto",
    "Elements": "Elementos",
    "Document": "Documento",
    "References": "Referencias",
    "Export": "Exportar",
    "View": "Ver",
    "Templates": "Plantillas",
    "Help": "Ayuda",
    "Language": "Idioma",
    # --- submenu titles ---
    "Heading": "Título",
    "Callout": "Llamado",
    "Indexes": "Índices",
    "Theme": "Tema",
    "Page size": "Tamaño de página",
    "Citation style": "Estilo de cita",
    "Apply template": "Aplicar plantilla",
    "Delete template": "Eliminar plantilla",
    # --- File menu ---
    "New": "Nuevo",
    "Open...": "Abrir...",
    "Save": "Guardar",
    "Save As...": "Guardar como...",
    "Reload": "Recargar",
    "Close Tab": "Cerrar pestaña",
    "Quit": "Salir",
    # --- Text menu ---
    "Heading 1": "Título 1",
    "Heading 2": "Título 2",
    "Heading 3": "Título 3",
    "Heading 4": "Título 4",
    "Heading 5": "Título 5",
    "Heading 6": "Título 6",
    "Remove heading": "Quitar título",
    "Bold": "Negrita",
    "Italic": "Cursiva",
    "Inline code": "Código en línea",
    "Link...": "Enlace...",
    # --- Elements menu ---
    "Section heading with label": "Título de sección con etiqueta",
    "Figure (skeleton)": "Figura (esqueleto)",
    "Image from file...": "Imagen desde archivo...",
    "Table": "Tabla",
    "Checklist": "Lista de tareas",
    "Two-column block": "Bloque de dos columnas",
    "Three-column block": "Bloque de tres columnas",
    "Equation": "Ecuación",
    "Footnote": "Nota al pie",
    "Code block": "Bloque de código",
    "Callout: Note": "Llamado: Nota",
    "Callout: Tip": "Llamado: Sugerencia",
    "Callout: Warning": "Llamado: Advertencia",
    "Callout: Important": "Llamado: Importante",
    "Callout: Caution": "Llamado: Precaución",
    "Page break": "Salto de página",
    "Section break (Roman i, ii, iii)": "Salto de sección (romano i, ii, iii)",
    "Section break (Arabic 1, 2, 3)": "Salto de sección (arábigo 1, 2, 3)",
    "Table of contents  [[toc]]": "Tabla de contenidos  [[toc]]",
    "List of figures  [[lof]]": "Lista de figuras  [[lof]]",
    "List of tables  [[lot]]": "Lista de tablas  [[lot]]",
    "List of equations  [[loe]]": "Lista de ecuaciones  [[loe]]",
    # --- References menu ---
    "Insert reference...": "Insertar referencia...",
    "Link bibliography (.bib)...": "Enlazar bibliografía (.bib)...",
    "New bibliography entry...": "Nueva entrada bibliográfica...",
    "(no document open)": "(no hay documento abierto)",
    "(no labels in this file)": "(no hay etiquetas en este archivo)",
    "Citations": "Citas",
    "Figures": "Figuras",
    "Tables": "Tablas",
    "Equations": "Ecuaciones",
    "Sections": "Secciones",
    # --- Export menu ---
    "Export as PDF...": "Exportar como PDF...",
    "Export as HTML...": "Exportar como HTML...",
    "Export as DOCX...": "Exportar como DOCX...",
    "Print...": "Imprimir...",
    "Export via epy_docs...": "Exportar con epy_docs...",
    # --- View menu ---
    "Page view": "Vista de página",
    # theme display names
    "Academic": "Académico",
    "Classic": "Clásico",
    "Corporate": "Corporativo",
    "Creative": "Creativo",
    "Handwritten": "Manuscrito",
    "Minimal": "Minimalista",
    "Professional": "Profesional",
    "Scientific": "Científico",
    "Technical": "Técnico",
    # page sizes
    "Letter": "Carta",
    "Legal": "Oficio",
    # --- Document menu ---
    "Document properties…": "Propiedades del documento…",
    # --- Templates menu ---
    "Save current settings as template…":
        "Guardar la configuración actual como plantilla…",
    # --- Help menu ---
    "User manual (English)": "Manual de usuario (Inglés)",
    "User manual (Spanish)": "Manual de usuario (Español)",
    "About epy_mdr…": "Acerca de epy_mdr…",
    # --- dialog window titles ---
    "Insert checklist": "Insertar lista de tareas",
    "Insert two-column block": "Insertar bloque de dos columnas",
    "Insert three-column block": "Insertar bloque de tres columnas",
    "Insert figure": "Insertar figura",
    "Insert table": "Insertar tabla",
    "Insert equation": "Insertar ecuación",
    "Insert footnote": "Insertar nota al pie",
    "Insert cross-reference": "Insertar referencia cruzada",
    "New bibliography entry": "Nueva entrada bibliográfica",
    "Export via epy_docs": "Exportar con epy_docs",
    "Document properties": "Propiedades del documento",
    "About epy_mdr": "Acerca de epy_mdr",
    # --- common dialog labels / buttons ---
    "Caption:": "Título:",
    "Reference ID:": "ID de referencia:",
    "Path:": "Ruta:",
    "Width:": "Ancho:",
    "Columns:": "Columnas:",
    "Data rows:": "Filas de datos:",
    "Include header row": "Incluir fila de encabezado",
    "Items:": "Elementos:",
    "Title:": "Título:",
    "Left column width:": "Ancho de columna izquierda:",
    "Left column content…": "Contenido de la columna izquierda…",
    "Right column content…": "Contenido de la columna derecha…",
    "Left column": "Columna izquierda",
    "Right column": "Columna derecha",
    "Column 1 width:": "Ancho de columna 1:",
    "Column 2 width:": "Ancho de columna 2:",
    "Column 1": "Columna 1",
    "Column 2": "Columna 2",
    "Column 3": "Columna 3",
    "First column content…": "Contenido de la columna 1…",
    "Second column content…": "Contenido de la columna 2…",
    "Third column content…": "Contenido de la columna 3…",
    "Note text:": "Texto de la nota:",
    "LaTeX body:": "Cuerpo LaTeX:",
    "Pick a label to insert as <code>@label</code>. Type to filter.":
        "Elija una etiqueta para insertar como <code>@label</code>. "
        "Escriba para filtrar.",
    "Browse...": "Examinar...",
    "Browse…": "Examinar…",
    "OK": "Aceptar",
    "Cancel": "Cancelar",
    # --- Document properties dialog ---
    "Title block": "Bloque de título",
    "Cover page": "Portada",
    "Running header (up to 6 cells)": "Encabezado (hasta 6 celdas)",
    "Footer": "Pie de página",
    "Subtitle:": "Subtítulo:",
    "Author:": "Autor:",
    "Date:": "Fecha:",
    "Page size:": "Tamaño de página:",
    "Text:": "Texto:",
    "Render a dedicated cover page": "Generar una portada dedicada",
    'Stamp "Page X of Y"': 'Estampar "Página X de Y"',
    "Watermark:": "Marca de agua:",
    "Choose watermark image": "Elegir imagen de marca de agua",
    # --- About dialog ---
    "Quarto / Markdown editor with live preview":
        "Editor de Quarto / Markdown con vista previa en vivo",
    "Close": "Cerrar",
    # --- epy_docs export dialog ---
    "Preview:": "Vista previa:",
    "Entry type:": "Tipo de entrada:",
    "Layout:": "Diseño:",
    "Document type:": "Tipo de documento:",
    "Output directory:": "Directorio de salida:",
    "Output formats:": "Formatos de salida:",
    # --- bibliography entry dialog: field labels ---
    "Citation key *": "Clave de cita *",
    "Author(s)": "Autor(es)",
    "Editor(s)": "Editor(es)",
    "Title": "Título",
    "Journal": "Revista",
    "Book title / proceedings": "Título del libro / actas",
    "Publisher": "Editorial",
    "Institution": "Institución",
    "School / university": "Escuela / universidad",
    "Organization": "Organización",
    "Year": "Año",
    "Month": "Mes",
    "Volume": "Volumen",
    "Number / issue": "Número",
    "Pages": "Páginas",
    "Edition": "Edición",
    "Chapter": "Capítulo",
    "Address (city)": "Dirección (ciudad)",
    "How published": "Cómo se publicó",
    "URL access date": "Fecha de acceso de la URL",
    "Note": "Nota",
    # --- bibliography entry dialog: group titles ---
    "Identity": "Identidad",
    "Venue": "Publicación",
    "Date": "Fecha",
    "Details": "Detalles",
    "Location": "Ubicación",
    "Identifiers": "Identificadores",
    # --- bibliography entry dialog: dynamic + messages ---
    "Required for @{type}: key, {fields}.":
        "Requeridos para @{type}: key, {fields}.",
    "Required for @{type}: key.": "Requeridos para @{type}: key.",
    "Missing required fields": "Faltan campos requeridos",
    "These fields are required for @{type}: {fields}":
        "Estos campos son requeridos para @{type}: {fields}",
    "Key already exists": "La clave ya existe",
    "The key {key} is already in the linked .bib file. Append anyway?":
        "La clave {key} ya está en el archivo .bib enlazado. "
        "¿Agregar de todas formas?",
    # --- file-picker dialog titles ---
    "Select output directory": "Seleccionar directorio de salida",
    "Select image": "Seleccionar imagen",
    "Choose logo image": "Elegir imagen del logo",
    # --- field placeholders ---
    "Optional title…": "Título opcional…",
    "Figure caption": "Título de la figura",
    "Optional caption…": "Título opcional…",
    "Footnote text": "Texto de la nota",
    "Filter: fig, tbl, eq, sec, or any substring":
        "Filtrar: fig, tbl, eq, sec, o cualquier subcadena",
    "e.g. 1, beam-section": "p. ej. 1, beam-section",
    "e.g. 1, beam-properties": "p. ej. 1, beam-properties",
    "e.g. 1, source-note": "p. ej. 1, source-note",
    "e.g. 1, euler-beam": "p. ej. 1, euler-beam",
    "top-left": "sup. izq.",
    "top-center": "sup. centro",
    "top-right": "sup. der.",
    "bottom-left": "inf. izq.",
    "bottom-center": "inf. centro",
    "bottom-right": "inf. der.",
    # --- theme editor dialog ---
    "Theme editor": "Editor de temas",
    "Name:": "Nombre:",
    "Based on:": "Basado en:",
    "Colors": "Colores",
    "Page background": "Fondo de página",
    "Headings": "Títulos",
    "Primary / accent": "Primario / acento",
    "Link / secondary": "Enlace / secundario",
    "Border": "Borde",
    "Code background": "Fondo de código",
    "Highlight": "Resaltado",
    "Fonts": "Fuentes",
    "Text font:": "Fuente de texto:",
    "Code font:": "Fuente de código:",
    "Typography (pt)": "Tipografía (pt)",
    "Body": "Cuerpo",
    "Caption": "Leyenda",
    "Callout colors": "Colores de llamados",
    "Background": "Fondo",
    "Tip": "Sugerencia",
    "Warning": "Advertencia",
    "Important": "Importante",
    "Caution": "Precaución",
    "Preview": "Vista previa",
    "Pick a color": "Elegir un color",
    "My theme": "Mi tema",
    "Please enter a name for the theme.": "Ingrese un nombre para el tema.",
    "New theme…": "Tema nuevo…",
    "Edit current theme…": "Editar el tema actual…",
    "Delete custom theme…": "Eliminar tema personalizado…",
    "Theme:": "Tema:",
    "Theme saved: {name}": "Tema guardado: {name}",
    "Delete the custom theme {name}?":
        "¿Eliminar el tema personalizado {name}?",
    "No custom themes to delete.":
        "No hay temas personalizados para eliminar.",
}


def tr(text: str) -> str:
    """Return ``text`` in the current language (English is the identity)."""
    if _lang == "en":
        return text
    return _ES.get(text, text)


def set_language(lang: str) -> None:
    """Switch the active language and relabel every registered widget."""
    global _lang
    if lang not in LANGUAGES or lang == _lang:
        return
    _lang = lang
    for callback in list(_observers):
        callback()


def current_language() -> str:
    """Return the active language code."""
    return _lang


def on_language_changed(callback: Callable[[], None]) -> None:
    """Register a relabel callback fired on every language change."""
    _observers.append(callback)


def translate_widget(root) -> None:
    """Translate the window title and labelled children of a widget tree.

    Reads the current language at call time, so it is meant to be called at
    the end of a modal dialog's ``__init__`` (dialogs are rebuilt each time
    they open). Only strings present in ``_ES`` change; everything else —
    user data, untranslated labels, rich content — passes through unchanged.
    """
    if _lang == "en":
        return
    from PySide6.QtWidgets import (
        QAbstractButton,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
    )

    title = root.windowTitle()
    if title:
        root.setWindowTitle(tr(title))
    for label in root.findChildren(QLabel):
        text = label.text()
        if text:
            label.setText(tr(text))
    for button in root.findChildren(QAbstractButton):
        text = button.text()
        if text:
            button.setText(tr(text))
    for box in root.findChildren(QGroupBox):
        text = box.title()
        if text:
            box.setTitle(tr(text))
    for field in root.findChildren(QLineEdit):
        placeholder = field.placeholderText()
        if placeholder:
            field.setPlaceholderText(tr(placeholder))
    for area in root.findChildren(QPlainTextEdit):
        placeholder = area.placeholderText()
        if placeholder:
            area.setPlaceholderText(tr(placeholder))
