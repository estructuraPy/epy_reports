# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for epy_mdr: portable onedir build.

import pypandoc
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

datas = []
datas += collect_data_files("pypandoc", include_py_files=False)
datas += collect_data_files("epy_mdr", include_py_files=False)

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

a = Analysis(
    ["src/epy_mdr/__main__.py"],
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
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="epy_mdr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="epy_mdr",
)
