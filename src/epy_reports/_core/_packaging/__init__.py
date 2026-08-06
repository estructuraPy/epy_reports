"""Build and release tooling for epy_reports (dev-only, wheel-excluded).

Layout — identical in epy_reports / epy_slides / epy_papers (same
folders, same tool names; only the reference-document format differs):

    assets_build/            — source images for the application icon.
    capture_screenshots/     — capture the bundled user-manual screenshots
                               into ``_config/_assets/screenshots/``.
    linux/build_deb.py       — pure-Python .deb package assembler.
    make_icon/               — generate ``assets_build/epy_reports.ico``
                               (+ .png) from the source logo.
    make_reference_docx/     — regenerate the per-theme Word reference
                               documents under
                               ``_config/_assets/reference_docx/``.
    windows/epy_reports.iss  — Inno Setup script for the Windows installer.
    dist/                    — gitignored installer build output.

None of this ships in the wheel — see ``force-exclude`` in
``[tool.hatch.build.targets.wheel]`` (``pyproject.toml``). Every tool is a
package run from a source checkout
(``python src/epy_reports/_core/_packaging/<tool>/__init__.py``), matching
the CI invocations in ``.github/workflows/installers.yml``.
"""
