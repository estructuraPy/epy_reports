"""Bundled branding images for epy_mdr.

Contains:
    epy_mdr.png       — application logo / window icon (704x524)
    estructurapy.png  — estructuraPy org logo (315x154)
    imagotipo_anm.png — ANM Ingenieria logotype (1100x677)

Use ``importlib.resources.files`` to read these images so they work both
from a source install and from a frozen PyInstaller build (zip archive)::

    from importlib.resources import files
    data = (files("epy_mdr.assets.branding") / "epy_mdr.png").read_bytes()
"""
