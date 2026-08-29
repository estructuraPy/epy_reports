"""The Windows system-ICU pin, now owned by epy_export.

The workaround itself moved -- it lived here and identically in
epy_slides and epy_papers, two of those copies documenting that they
mirrored this one. What stays this package's business is that the pin
is CALLED, and called before anything touches Qt.

So these tests changed shape on purpose: they no longer test the
function (epy_export does that), they test the wiring. A function that
is correct and not connected is the same as a function that is not
there, and importing this package is the only place that ordering can
be asserted.

The regression being guarded is still the same one: ``ImportError: DLL
load failed ... WinError 127``, from conda's ICU shadowing the Windows
copy Qt6Core is linked against.
"""

import epy_reports


def test_the_package_reaches_the_shared_pin():
    # The wiring, not the function. Planting the defect -- deleting the
    # call from __init__ -- must fail something, and this is what.
    assert hasattr(epy_reports, "pin_system_icu")
    from epy_export import pin_system_icu

    assert epy_reports.pin_system_icu is pin_system_icu


def test_the_pin_is_reentrant():
    """Calling it again after package import must be a no-op."""
    epy_reports.pin_system_icu()
    epy_reports.pin_system_icu()


def test_qt_imports_after_the_package_is_imported():
    """Qt must load once importing this package has pinned ICU.

    The strongest statement available here, and it is not a formality:
    in this conda environment PySide6.QtCore raises WinError 127 without
    the pin -- measured when epy_export's own Qt tests skipped the whole
    file until the call was added.
    """
    from PySide6 import QtCore  # noqa: PLC0415

    assert QtCore.qVersion()
