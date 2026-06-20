# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for epy_reports: portable onedir build.

from pathlib import Path as _Path
import pypandoc

_ICON = str(_Path("assets_build/epy_reports.ico"))
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

datas = []
datas += collect_data_files("pypandoc", include_py_files=False)
# epy_reports is built from src/ via pathex (it may not be pip-installed), so
# collect_data_files cannot resolve it reliably — bundle the assets tree
# explicitly. Keeping the epy_reports/assets/... layout preserves
# importlib.resources lookups at runtime.
_ASSETS = _Path("src/epy_reports/assets")
datas += [
    (str(p), str(_Path("epy_reports") / p.relative_to("src/epy_reports").parent))
    for p in _ASSETS.rglob("*")
    if p.is_file() and p.suffix != ".py"
]

binaries = []
binaries += collect_dynamic_libs("pypandoc")

# pypandoc-binary ships pandoc.exe inside its package; collect_data_files
# skips executables, so we add it by hand to the location pypandoc looks
# at runtime ({pypandoc}/files/pandoc.exe).
_pandoc = pypandoc.get_pandoc_path()
if not _pandoc.lower().endswith(".exe"):
    _pandoc += ".exe"
binaries.append((_pandoc, "pypandoc/files"))

hiddenimports = []
hiddenimports += collect_submodules("pypandoc")
# importlib.resources.files("epy_reports.assets.themes") imports these packages
# dynamically; PyInstaller cannot detect that statically.
hiddenimports += [
    "epy_reports.assets",
    "epy_reports.assets.branding",
    "epy_reports.assets.themes",
    "epy_reports.assets.reference_docx",
    "epy_reports.assets.mathjax",
    "epy_reports.assets.csl",
    "epy_reports.assets.mermaid",
    "epy_reports.assets.nomnoml",
    # Lazy-imported inside _pdf_footer.add_watermark for the grayscale
    # watermark; PyInstaller may miss the in-function import.
    "PIL",
    "PIL.Image",
]

a = Analysis(
    ["src/epy_reports/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "test",
        "unittest",
        # The build env may carry other Qt bindings (PyQt5 via matplotlib,
        # pulled in by sibling libs). epy_reports uses PySide6 exclusively.
        "PyQt5",
        "PyQt6",
        # Heavy scientific stack reachable through optional epy_docs paths;
        # never imported by the frozen editor itself.
        "matplotlib",
        "pandas",
        "numpy",
        "epy_docs",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="epy_reports",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=_ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="epy_reports",
)
