# Shared PySide6/Qt Runtime — epy_reports

## What it is

epy_reports and epy_slides are both PySide6/Qt desktop apps that ship identical
~150 MB PyInstaller `_internal/` bundles. When both are installed, the installer
can share a single copy of that runtime, saving approximately 150 MB per machine.

## How it works

### Install-time flow

1. The installer detects whether epy_slides is already installed by looking for
   `%LOCALAPPDATA%\Programs\epy_slides\_internal\PySide6\Qt6Core.dll`.

2. It reads the FileVersion from that DLL and from the DLL bundled with this
   installer (`dist\epy_reports\_internal\PySide6\Qt6Core.dll`).

3. **If versions match**: a custom wizard page is shown with the checkbox

   > [x] Share the PySide6/Qt runtime with epy_slides  (recommended)

   pre-checked. An observation text explains what sharing does and how to undo it.

4. **If versions do not match, or epy_slides is absent**: the checkbox is shown
   but disabled, and the observation explains that epy_slides must be installed
   first (or both apps must be rebuilt against the same PySide6 version).

5. When the user proceeds with sharing enabled:

   a. The installer copies `_internal/` to the shared location:
      ```
      %LOCALAPPDATA%\Programs\epy_shared_runtime\<qt-version>\_internal\
      ```
      A robocopy mirror is used; this is a no-op if the shared dir already exists
      (i.e., epy_slides already populated it).

   b. The just-installed `%LOCALAPPDATA%\Programs\epy_reports\_internal\`
      directory is deleted.

   c. A **directory junction** is created at the deleted path, pointing to the
      shared location:
      ```
      %LOCALAPPDATA%\Programs\epy_reports\_internal  ->
        %LOCALAPPDATA%\Programs\epy_shared_runtime\<qt-version>\_internal\
      ```
      Junctions work without administrator rights on any local NTFS volume.
      The app executable resolves `_internal\` at launch exactly as before —
      it does not know or care that the directory is a junction.

   d. A reference count is incremented in the registry:
      ```
      HKCU\Software\epy_suite\shared_runtime
        qt_version  REG_SZ    "6.11.1.0"
        refcount    REG_DWORD  2
      ```

6. When the user declines sharing (unchecks the box), installation proceeds
   identically to the original behavior: `_internal/` is installed as a real
   directory inside `%LOCALAPPDATA%\Programs\epy_reports\`. No junction, no
   shared dir, no registry key.

### Uninstall-time flow

1. The uninstaller checks whether `HKCU\Software\epy_suite\shared_runtime`
   exists.

2. If it does: the junction at `{app}\_internal` is removed via `rmdir`
   (which removes only the junction link, not the shared directory target).
   The refcount is decremented.

3. If the refcount reaches 0 (last consumer uninstalling):
   - The shared directory is deleted (`DelTree`).
   - The versioned parent and `epy_shared_runtime` root are cleaned up if empty.
   - The registry key is removed.

4. If the key does not exist: Inno's normal uninstall removes `{app}\_internal`
   as an ordinary directory — same as before this feature was added.

## When the option is offered

| Condition | Checkbox state |
|-----------|---------------|
| epy_slides installed, same Qt version | Enabled, checked (recommended) |
| epy_slides installed, different Qt version | Disabled, unchecked |
| epy_slides not installed | Disabled, unchecked |

## Limitations and honest caveats

1. **The shared dir is not version-controlled by the installer's uninstall log.**
   Inno Setup's uninstall log only tracks files installed by the `[Files]`
   section. The shared dir and junction are created/removed entirely in
   `[Code]` Pascal, so if the installer process crashes after copying but
   before writing the refcount, the shared dir may be left behind. This is
   a stranded ~150 MB directory, not a broken install — the app continues
   to work through its self-contained `_internal/`. Manual cleanup: delete
   `%LOCALAPPDATA%\Programs\epy_shared_runtime\`.

2. **Version-mismatch guard is runtime, not build-time.**
   The version check at `ssPostInstall` reads the DLL that was just installed
   on disk. If someone manually replaces DLLs after install, the guard at
   next installer run may be confused. This is an edge case that requires
   manual intervention.

3. **The refcount is advisory, not atomic.**
   If two installers run simultaneously (unlikely for a per-user desktop app),
   the refcount increment could race. The consequence is at worst an incorrect
   count; the shared dir would be deleted prematurely on uninstall or left
   behind. In practice these are serial per-user desktop installs.

4. **Uninstalling epy_slides while epy_reports uses the shared dir.**
   If epy_slides was installed with sharing and is uninstalled first, it
   removes its junction and decrements the count. If epy_reports is still
   installed and its refcount is 1, the shared dir is deleted on epy_slides
   uninstall, breaking epy_reports' junction. Both apps must cooperate:
   install both with sharing, uninstall one at a time; the last one removes
   the shared dir cleanly.
   **Mitigation**: install epy_reports last (so it holds refcount 1 until
   it is uninstalled). The installers always increment the count regardless
   of install order, so the last-to-uninstall always cleans up.

5. **Not verified on a clean machine without either app installed.**
   The compile step (ISCC) has been run and passes. End-to-end on-machine
   testing requires: (a) fresh user profile or clean `%LOCALAPPDATA%\Programs\`,
   (b) install epy_reports without epy_slides (observe disabled checkbox),
   (c) install epy_slides (observe enabled checkbox, accept), (d) verify
   junction exists and both apps launch, (e) uninstall one, verify other
   still works, (f) uninstall last, verify shared dir removed.

## Approach comparison (why option a was chosen)

| Option | Description | Verdict |
|--------|-------------|---------|
| **(a) Shared dir + junction** | Shared versioned dir; junction at each app's `_internal` | **Chosen**: no admin required, reversible, no app source changes |
| (b) Unified suite installer | One installer for both apps over one runtime | Rejected: couples release cycles of two separate git repos |
| (c) Junction reuse of sibling's `_internal` | Point `epy_reports\_internal` directly at `epy_slides\_internal` | Rejected: uninstalling epy_slides would delete the target, breaking epy_reports |

Option (a) with a neutral versioned directory as the shared target is the only
approach where uninstalling either app in either order remains safe.
