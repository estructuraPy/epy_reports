# Third-Party Notices and Asset Licensing

epy_reports's **source code** is licensed under the MIT License (see
[LICENSE](LICENSE)). The distributed application bundles or links the
following third-party components, each governed by its own license.

## Bundled / linked components

| Component | License | Notes |
|---|---|---|
| [Qt for Python (PySide6)](https://www.qt.io/qt-for-python) | LGPL-3.0 | Dynamically linked. The frozen distribution keeps the Qt shared libraries as separate files (PyInstaller onedir layout), so they can be replaced as required by the LGPL. Source: <https://code.qt.io/> |
| [Pandoc](https://github.com/jgm/pandoc) | GPL-2.0-or-later | Distributed as a separate, unmodified executable (`pandoc.exe`) invoked as an external tool — mere aggregation, not a derived work. Source code: <https://github.com/jgm/pandoc> |
| [pypandoc](https://github.com/JessicaTegner/pypandoc) | MIT | Python wrapper used to call Pandoc. |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause | Reads and rewrites the exported PDF to stamp footers / page numbers. |
| [ReportLab](https://www.reportlab.com/) | BSD-3-Clause | Draws the footer overlay merged onto each exported PDF page. |
| [Pillow](https://python-pillow.org/) | MIT-CMU | Build-time only (icon generation); not shipped in the application. |
| [PyInstaller](https://pyinstaller.org/) | GPL-2.0 with bootloader exception | Build-time only; the exception explicitly permits distributing frozen applications under any license. |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | Inno Setup License | Build-time only (Windows installer compiler). |

## Proprietary assets (NOT covered by the MIT license)

The following bundled assets are Copyright (c) 2026
**Ing. Angel Navarro-Mora M.Sc. / ANM Ingeniería (estructuraPy)** —
**all rights reserved**:

- `src/epy_reports/assets/branding/` — application logo and the
  ANM Ingeniería / estructuraPy brand images.
- `src/epy_reports/assets/themes/*.epyson` — layout theme definitions.
- `src/epy_reports/assets/reference_docx/*.docx` — Word reference
  (style) templates.
- `assets_build/` — source images for the application icon.

These assets are licensed to you **only for use as an integral part of
unmodified epy_reports distributions**. Extracting, modifying, rebranding,
or redistributing them separately — in particular for use with other
document-generation products — requires prior written permission from
ANM Ingeniería (<ahnavarro@anmingenieria.com>).

## epy_docs backend

The optional `epy_docs` rendering backend is a separate, commercial,
privately distributed product of ANM Ingeniería. It is **not** included
in this repository or in the binary distributions of epy_reports.
