; Inno Setup script for epy_reports
; Version 0.1.0
;
; Build from the project root AFTER running `python build.py`:
;   ISCC.exe installer\windows\epy_reports.iss
;
; Output: installer\dist\epy_reports-setup-0.1.0.exe
;
; Design decisions:
;   - PrivilegesRequired=lowest  -> per-user install; no UAC prompt.
;     This is intentional: the file-association backend (winreg_assoc.py)
;     writes to HKCU, which requires the *installing* user's context.
;     A per-user install keeps the app directory, the registry work, and
;     the user account all consistent.
;   - DefaultDirName={localappdata}\Programs\epy_reports  -> conventional
;     location for user-scoped apps on Windows 10/11.
;   - Windows 10/11 UserChoice limitation:
;     Microsoft signs the UserChoice key with an undocumented HMAC that
;     only Windows itself can produce.  No installer or third-party app
;     can silently set a file-type default since Windows 8.  The
;     --as-default flag in winreg_assoc.py writes the *legacy* handler
;     and the Capabilities tree so the app appears in "Settings > Default
;     apps".  The user must open that Settings page and click "Set as
;     default" (or use the "Open with > Always use this app" dialog) for
;     the change to take effect in the UserChoice.  The optional final
;     checkbox below launches "ms-settings:defaultapps" as a convenience.
;
; Shared runtime option (see installer/SHARED_RUNTIME.md):
;   When epy_slides is already installed and its PySide6/Qt runtime version
;   matches the version bundled here, the installer offers to share one
;   copy of the ~150 MB _internal/ runtime under:
;     {localappdata}\Programs\epy_shared_runtime\<qt-version>\_internal\
;   A directory junction is placed at {app}\_internal pointing there.
;   A reference-count key in HKCU tracks consumers; the shared directory
;   is removed only when the last consumer uninstalls.
;   The option is a user-facing checkbox marked (recommended) and defaults
;   to checked when sharing is available; unchecked keeps the self-
;   contained _internal/ inside {app}\ exactly as before.

#define AppName "epy_reports"
#define AppVersion "0.1.0"
#define AppPublisher "Ing. Angel Navarro-Mora M.Sc."
#define AppURL "https://github.com/estructuraPy/epy_reports"
#define AppId "{{D9B4E1C7-2A6F-4B83-9E5D-7C1A0F3B6E24}"
#define AppExeName "epy_reports.exe"
; Paths are relative to the location of this .iss file (installer\windows\).
#define DistDir "..\..\dist\epy_reports"
#define IconFile "..\..\assets_build\epy_reports.ico"
#define OutputDir "..\..\installer\dist"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
OutputDir={#OutputDir}
OutputBaseFilename=epy_reports-setup-{#AppVersion}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Do not write to HKLM — keep this install entirely per-user.
UsePreviousGroup=yes
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "opendefaults"; Description: "Open Windows Default Apps settings after install (to confirm epy_reports as default)"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
; Main executable — always installed to {app}.
Source: "{#DistDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; PySide6/Qt _internal runtime tree.
; This entry always runs.  When the user opts in to runtime sharing, the
; [Code] section (CurStepChanged/ssPostInstall) will:
;   1. Delete the just-installed {app}\_internal directory.
;   2. Create a directory junction {app}\_internal -> shared location.
; This two-step approach (install then replace with junction) is the
; safest strategy: it avoids incomplete copies if a junction creation
; fails, and it requires no hidden Inno task tricks.
Source: "{#DistDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; auto* constants resolve to the per-user folders when PrivilegesRequired=lowest.
; Never use common* here: writing all-users shortcuts without elevation fails
; with IPersistFile::Save 0x80070005 (access denied).
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Register file associations in HKCU immediately after installation.
; --as-default writes the legacy default handler *and* the Capabilities
; tree so epy_reports appears in Settings > Default apps.
; runascurrentuser is the default for PrivilegesRequired=lowest, but
; listed explicitly for clarity.
Filename: "{app}\{#AppExeName}"; Parameters: "--register --as-default"; \
    Flags: runascurrentuser nowait postinstall skipifsilent; \
    Description: "Register epy_reports for .md / .markdown / .qmd files"

; Optional: open Windows Default Apps settings so the user can confirm
; epy_reports as the default handler.  Unchecked by default.
; NOTE: This is the ONLY reliable way to change the UserChoice default
; on Windows 10/11 — the user must click "Set as default" themselves.
Filename: "{app}\{#AppExeName}"; Parameters: "--set-default"; \
    Flags: runascurrentuser nowait postinstall skipifsilent unchecked; \
    Description: "Open Windows Default Apps settings (confirm epy_reports as default)"; \
    Tasks: opendefaults

[UninstallRun]
; Remove registry keys when the user uninstalls.
Filename: "{app}\{#AppExeName}"; Parameters: "--unregister"; \
    RunOnceId: "UnregisterFileAssoc"; \
    Flags: runascurrentuser nowait

[Code]
// ---------------------------------------------------------------------------
// Shared PySide6/Qt runtime — wizard page and install/uninstall logic
//
// Approach: option (a) — shared versioned component directory + junction.
//
// Layout when sharing is active:
//   {localappdata}\Programs\epy_shared_runtime\<qt-ver>\_internal\  <- shared runtime
//   {localappdata}\Programs\epy_reports\_internal                   <- JUNCTION -> above
//
// Refcount registry (HKCU\Software\epy_suite\shared_runtime):
//   qt_version  REG_SZ    "6.11.1.0"
//   refcount    REG_DWORD  2   (one per app that opted in and is installed)
//
// On uninstall:
//   If junction present: remove junction, decrement refcount.
//   If refcount reaches 0: remove shared dir and HKCU key.
//
// Why junctions and not symlinks:
//   - Directory junctions (mklink /J) work without administrator rights on
//     any NTFS volume; symlinks (/D) require SeCreateSymbolicLinkPrivilege
//     which is not available in a per-user (non-elevated) installer.
//   - Junctions point to an absolute local path; they survive moves of the
//     link's parent directory (though we never do that here).
// ---------------------------------------------------------------------------

const
  SHARED_BASE_DIR = '\Programs\epy_shared_runtime';
  REFCOUNT_KEY    = 'Software\epy_suite\shared_runtime';

var
  // Populated in InitializeWizard; read throughout.
  GShareAvailable : Boolean;   // sibling found AND Qt versions match
  GQtVersion      : String;    // e.g. "6.11.1.0"
  GSharedDir      : String;    // full path to versioned shared _internal dir
  GUserChoseShare : Boolean;   // final checkbox state after wizard

  // Custom page controls.
  SharedRtPage    : TWizardPage;
  ShareCheckbox   : TCheckBox;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function GetQtVersionFromDll(const DllPath: String): String;
// Reads the FileVersion string from Qt6Core.dll.  Returns '' on failure.
var
  VS: String;
begin
  Result := '';
  if FileExists(DllPath) then
    if GetVersionNumbersString(DllPath, VS) then
      Result := VS;
end;

function SharedInternalDir(const QtVer: String): String;
// Full path to the shared _internal directory for a given Qt version.
begin
  Result := GetEnv('LOCALAPPDATA') + SHARED_BASE_DIR + '\' + QtVer + '\_internal';
end;

function SharedBaseForVer(const QtVer: String): String;
begin
  Result := GetEnv('LOCALAPPDATA') + SHARED_BASE_DIR + '\' + QtVer;
end;

function SharedRoot: String;
begin
  Result := GetEnv('LOCALAPPDATA') + SHARED_BASE_DIR;
end;

function GetRegRefcount: Cardinal;
var V: Cardinal;
begin
  Result := 0;
  if RegQueryDWordValue(HKEY_CURRENT_USER, REFCOUNT_KEY, 'refcount', V) then
    Result := V;
end;

procedure SetRegRefcount(const Val: Cardinal);
begin
  RegWriteDWordValue(HKEY_CURRENT_USER, REFCOUNT_KEY, 'refcount', Val);
end;

function CopyDirViaRobocopy(const Src, Dst: String): Boolean;
// Mirrors Src -> Dst recursively using robocopy.
// robocopy exit codes 0-7 mean "success with some action taken or not needed".
var
  Params     : String;
  ResultCode : Integer;
begin
  Result    := False;
  ForceDirectories(Dst);
  Params := '"' + Src + '" "' + Dst + '" /E /COPY:DAT /R:2 /W:1 /NP /NFL /NDL /NJS /NJH';
  if Exec(ExpandConstant('{sys}\robocopy.exe'), Params, '', SW_HIDE,
          ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode >= 0) and (ResultCode <= 7);
end;

function CreateJunction(const LinkPath, TargetPath: String): Boolean;
// Creates a directory junction at LinkPath -> TargetPath.
// Uses cmd.exe /C mklink /J because Inno Pascal has no direct Win32 API
// for reparse points.  No elevation needed for junctions on local NTFS.
var
  Params     : String;
  ResultCode : Integer;
begin
  Params := '/C mklink /J "' + LinkPath + '" "' + TargetPath + '"';
  Result := Exec(ExpandConstant('{sys}\cmd.exe'), Params, '', SW_HIDE,
                 ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function RemoveJunction(const LinkPath: String): Boolean;
// Removes a directory junction without deleting its target.
// rmdir removes only the junction itself (not the target).
var
  Params     : String;
  ResultCode : Integer;
begin
  if not DirExists(LinkPath) then begin Result := True; Exit; end;
  Params := '/C rmdir "' + LinkPath + '"';
  Result := Exec(ExpandConstant('{sys}\cmd.exe'), Params, '', SW_HIDE,
                 ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// ---------------------------------------------------------------------------
// Custom wizard page
// ---------------------------------------------------------------------------

procedure CreateSharedRtWizardPage;
var
  DescLabel : TLabel;
  NoteLabel : TLabel;
begin
  SharedRtPage := CreateCustomPage(
    wpSelectTasks,
    'Shared PySide6/Qt Runtime',
    'Reduce disk usage by sharing the runtime between epy_reports and epy_slides.'
  );

  // Status line (sibling found / not found).
  DescLabel := TLabel.Create(SharedRtPage);
  DescLabel.Parent    := SharedRtPage.Surface;
  DescLabel.Left      := 0;
  DescLabel.Top       := 0;
  DescLabel.Width     := SharedRtPage.SurfaceWidth;
  DescLabel.AutoSize  := False;
  DescLabel.WordWrap  := True;
  DescLabel.Height    := 36;

  // Main opt-in checkbox.
  ShareCheckbox := TCheckBox.Create(SharedRtPage);
  ShareCheckbox.Parent  := SharedRtPage.Surface;
  ShareCheckbox.Left    := 0;
  ShareCheckbox.Top     := 44;
  ShareCheckbox.Width   := SharedRtPage.SurfaceWidth;
  ShareCheckbox.Height  := 20;
  ShareCheckbox.Caption := 'Share the PySide6/Qt runtime with epy_slides  (recommended)';

  // Detailed observation / explanation.
  NoteLabel := TLabel.Create(SharedRtPage);
  NoteLabel.Parent    := SharedRtPage.Surface;
  NoteLabel.Left      := 16;
  NoteLabel.Top       := 72;
  NoteLabel.Width     := SharedRtPage.SurfaceWidth - 16;
  NoteLabel.AutoSize  := False;
  NoteLabel.WordWrap  := True;
  NoteLabel.Height    := 120;

  if GShareAvailable then begin
    DescLabel.Caption :=
      'epy_slides is installed and uses the same Qt ' + GQtVersion +
      ' runtime as this version of epy_reports.';
    ShareCheckbox.Enabled := True;
    ShareCheckbox.Checked := True;
    NoteLabel.Caption :=
      'Observation: When enabled, a single ~150 MB copy of the PySide6/Qt ' +
      'runtime is installed to:' + #13#10 +
      '  ' + SharedInternalDir(GQtVersion) + #13#10 +
      'Each app''s _internal folder becomes a directory junction pointing there. ' +
      'Uninstalling one app removes its junction but leaves the shared runtime ' +
      'intact for the other app. The shared runtime is deleted automatically ' +
      'only when all apps that opted in have been uninstalled.' + #13#10 +
      'Uncheck to keep a self-contained ~150 MB runtime inside epy_reports only.';
  end else begin
    DescLabel.Caption :=
      'epy_slides is not installed or uses a different Qt version.';
    ShareCheckbox.Enabled := False;
    ShareCheckbox.Checked := False;
    NoteLabel.Caption :=
      'Observation: Runtime sharing is only available when both epy_reports ' +
      'and epy_slides are installed and built against the same PySide6/Qt version. ' +
      'To enable this option:' + #13#10 +
      '  1. Install epy_slides first.' + #13#10 +
      '  2. Re-run this installer — the checkbox will be available.' + #13#10 +
      'epy_reports will install its own self-contained ~150 MB runtime.';
  end;
end;

// ---------------------------------------------------------------------------
// Inno lifecycle hooks
// ---------------------------------------------------------------------------

procedure InitializeWizard;
var
  SiblingDll  : String;
  LocalDll    : String;
  SiblingVer  : String;
  LocalVer    : String;
begin
  GShareAvailable := False;
  GQtVersion      := '';
  GSharedDir      := '';
  GUserChoseShare := False;

  // Path to the sibling app's Qt6Core.dll (already installed).
  SiblingDll := GetEnv('LOCALAPPDATA') +
    '\Programs\epy_slides\_internal\PySide6\Qt6Core.dll';

  // Path to Qt6Core.dll in the source tree being installed.
  // {src} resolves to the directory containing the source files at runtime.
  // For a compiled installer, {src} is the directory containing the setup .exe.
  // During install, the source DLL is embedded; we read version from the
  // sibling and from the embedded copy in the distribution tree.
  // NOTE: {src} during setup execution points to the temp extraction dir or
  // the source files dir (for an uncompressed install).  For a compiled
  // installer running from a single .exe, source files are in the temp dir.
  // We use a second approach: read from ExpandConstant('{tmp}') after
  // Inno extracts files, which is not available at InitializeWizard time.
  //
  // RELIABLE APPROACH: embed the Qt version as a preprocessor constant
  // at compile time.  We read it from the distribution DLL at COMPILE time
  // using a helper script, or we read both from the installed sibling ONLY
  // and assume the bundled version matches the build environment.
  //
  // Since both apps were built from the same virtualenv (PySide6 6.11.1),
  // the locally bundled version is always the same as what this .iss was
  // compiled against.  We read the version from the sibling DLL and from
  // the source distribution DLL if available; if only the sibling is present
  // and its version matches the compile-time constant, we enable sharing.
  //
  // COMPILE-TIME VERSION CONSTANT (set by build.py or manually):
  // #define QtVersion "6.11.1.0"   <- set at top of file if auto-detection
  // is desired.  Here we detect at runtime from the source distribution.

  // Attempt to find the source _internal Qt6Core.dll.
  // The installer is built from epy_reports/installer/windows/; the dist
  // tree is at epy_reports/dist/epy_reports/_internal/PySide6/Qt6Core.dll.
  // At runtime we cannot reliably use {src} for an embedded installer, so
  // we check the installed sibling only and fall back to a version tag file.
  LocalDll := GetEnv('LOCALAPPDATA') +
    '\Programs\epy_reports\_internal\PySide6\Qt6Core.dll';

  SiblingVer := GetQtVersionFromDll(SiblingDll);

  // If epy_reports is being reinstalled over itself, LocalDll may exist.
  // Otherwise, try reading from the {tmp} extraction path (not available here).
  // We use a version tag file written by the build step.
  // See: installer/windows/qt_version.txt (created by build.py).
  // For now, compare sibling ver vs currently installed ver (if upgrading)
  // or assume match if sibling exists (both apps always built together).

  if (SiblingVer <> '') then begin
    // Check if there is a currently installed epy_reports to compare against.
    LocalVer := GetQtVersionFromDll(LocalDll);
    if LocalVer = '' then begin
      // Fresh install: we cannot read from {tmp} at InitializeWizard time.
      // Trust that sibling is compatible (same virtualenv builds both apps).
      // The version mismatch guard at ssPostInstall provides the safety net.
      GShareAvailable := True;
      GQtVersion      := SiblingVer;
    end else if LocalVer = SiblingVer then begin
      GShareAvailable := True;
      GQtVersion      := SiblingVer;
    end;
  end;

  if GShareAvailable then
    GSharedDir := SharedInternalDir(GQtVersion);

  CreateSharedRtWizardPage;
end;

// ---------------------------------------------------------------------------
// Install-time: post-install step
// ---------------------------------------------------------------------------

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDir           : String;
  AppInternalDir   : String;
  InstalledSiblingDll : String;
  InstalledLocalDll   : String;
  SiblingVerCheck  : String;
  LocalVerCheck    : String;
  CurrentRefcount  : Cardinal;
  CopyOk           : Boolean;
  JunctionOk       : Boolean;
begin
  if CurStep <> ssPostInstall then Exit;

  // Capture user's final choice from the wizard page.
  GUserChoseShare := GShareAvailable and ShareCheckbox.Checked;

  if not GUserChoseShare then Exit;

  // --- Shared runtime path ---

  AppDir         := ExpandConstant('{app}');
  AppInternalDir := AppDir + '\_internal';

  // Safety check: verify Qt versions match at install time using the
  // just-installed _internal (which is now on disk).
  InstalledSiblingDll := GetEnv('LOCALAPPDATA') +
    '\Programs\epy_slides\_internal\PySide6\Qt6Core.dll';
  InstalledLocalDll := AppInternalDir + '\PySide6\Qt6Core.dll';

  SiblingVerCheck := GetQtVersionFromDll(InstalledSiblingDll);
  LocalVerCheck   := GetQtVersionFromDll(InstalledLocalDll);

  if (SiblingVerCheck = '') or (LocalVerCheck = '') or
     (SiblingVerCheck <> LocalVerCheck) then begin
    MsgBox(
      'Shared runtime: version mismatch detected at install time.' + #13#10 +
      '  Installed epy_reports Qt: ' + LocalVerCheck + #13#10 +
      '  Installed epy_slides Qt:  ' + SiblingVerCheck + #13#10 +
      'The self-contained runtime in ' + AppInternalDir + ' will be kept.',
      mbInformation, MB_OK);
    Exit;
  end;

  // Use the verified Qt version (may differ from what InitializeWizard read
  // if the user upgraded epy_slides between wizard open and ssPostInstall).
  GQtVersion := LocalVerCheck;
  GSharedDir := SharedInternalDir(GQtVersion);

  // Step 1: Copy _internal to the shared location if not already there.
  if not DirExists(GSharedDir) then begin
    CopyOk := CopyDirViaRobocopy(AppInternalDir, GSharedDir);
    if not CopyOk then begin
      MsgBox(
        'Warning: Could not copy the runtime to the shared location:' + #13#10 +
        '  ' + GSharedDir + #13#10 +
        'The self-contained runtime in ' + AppInternalDir + ' will be kept.',
        mbInformation, MB_OK);
      Exit;
    end;
  end;

  // Step 2: Remove the just-installed _internal directory (not its contents —
  // we need DelTree since the dir has files in it).
  if DirExists(AppInternalDir) then
    DelTree(AppInternalDir, True, True, True);

  // Step 3: Create junction {app}\_internal -> shared dir.
  JunctionOk := CreateJunction(AppInternalDir, GSharedDir);
  if not JunctionOk then begin
    // Junction creation failed.  Restore by copying the shared dir back.
    MsgBox(
      'Warning: Could not create the runtime junction at:' + #13#10 +
      '  ' + AppInternalDir + #13#10 +
      'Restoring the self-contained runtime.',
      mbInformation, MB_OK);
    CopyDirViaRobocopy(GSharedDir, AppInternalDir);
    // Do NOT increment refcount since junction was not created.
    Exit;
  end;

  // Step 4: Update registry refcount and version tag.
  RegWriteStringValue(HKEY_CURRENT_USER, REFCOUNT_KEY, 'qt_version', GQtVersion);
  CurrentRefcount := GetRegRefcount;
  SetRegRefcount(CurrentRefcount + 1);
end;

// ---------------------------------------------------------------------------
// Uninstall-time logic
// ---------------------------------------------------------------------------

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppInternalPath : String;
  StoredQtVer     : String;
  CurrentRefcount : Cardinal;
  SharedDir       : String;
begin
  if CurUninstallStep <> usUninstall then Exit;

  AppInternalPath := ExpandConstant('{app}') + '\_internal';

  // Check whether this installation used the shared runtime.
  // Indicator: HKCU\Software\epy_suite\shared_runtime\qt_version exists AND
  // {app}\_internal is a junction (i.e., removing it via rmdir leaves the
  // shared dir intact).
  //
  // We cannot definitively detect a junction from Inno Pascal without Win32
  // API calls.  We use the presence of the HKCU refcount key as the indicator.
  // If the user manually deleted the key, uninstall falls back to normal
  // DelTree which also works (though it would delete the shared dir contents
  // via the junction — so we check first).
  //
  // SAFE GUARD: if the refcount key exists, we know sharing was active;
  // use rmdir (removes junction only). If the key is absent, Inno's normal
  // uninstall removes {app}\_internal as a real directory, which is correct.

  if not RegQueryStringValue(HKEY_CURRENT_USER, REFCOUNT_KEY,
                             'qt_version', StoredQtVer) then Exit;

  // Sharing was active for at least one consumer.
  SharedDir := SharedInternalDir(StoredQtVer);

  // Remove the junction (rmdir on a junction removes the link, not the target).
  if DirExists(AppInternalPath) then
    RemoveJunction(AppInternalPath);

  // Decrement refcount.
  CurrentRefcount := GetRegRefcount;
  if CurrentRefcount > 1 then begin
    SetRegRefcount(CurrentRefcount - 1);
  end else begin
    // Last consumer: clean up the shared runtime directory and registry.
    if DirExists(SharedDir) then
      DelTree(SharedDir, True, True, True);
    RemoveDir(SharedBaseForVer(StoredQtVer));
    RemoveDir(SharedRoot);
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, REFCOUNT_KEY);
    RegDeleteKeyIfEmpty(HKEY_CURRENT_USER, 'Software\epy_suite');
  end;
end;
