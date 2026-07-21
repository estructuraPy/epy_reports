"""Optional bridges from epy_reports to sibling epy_* suite packages.

Modules here are the only ones in epy_reports that may reference another
``epy_*`` package by name. Every such reference is a real Python import,
but it is deferred to function-call time and guarded by an availability
check, so importing ``epy_reports`` never requires the sibling package to
be installed.
"""
