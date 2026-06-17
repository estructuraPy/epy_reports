# epy_mdr Installer Guide

## Overview

epy_mdr ships two installer formats:

| Platform | File | Tool |
|----------|------|------|
| Windows 10/11 | `installer/dist/epy_mdr-setup-0.4.1.exe` | Inno Setup |
| Ubuntu / Debian | `installer/dist/epy-mdr_0.4.1_all.deb` | pure-Python .deb assembler |

Both install the application and register it for `.md`, `.markdown`, and `.qmd` files.

---

## Prerequisites

### Common
```
pip install pillow          # required for icon generation
python installer/make_icon.py   # generates assets_build/epy_mdr.ico + .png
```

### Windows
- Python 3.10+
- `pip install pyinstaller pypandoc-binary`
- Inno Setup 6 (see below)

### Ubuntu
- Python 3.10+
- `pip install pypandoc-binary pillow`
- No additional tools needed for the .deb assembler

---

## Building Locally

### 1. Generate icons (required before any build)

```bash
python installer/make_icon.py
```

Produces `assets_build/epy_mdr.ico` (16/32/48/256 px) and `assets_build/epy_mdr.png` (256 x 256).

---

### 2. Windows installer

#### Step 1 — PyInstaller onedir build

```bash
python build.py
```

Output: `dist/epy_mdr/epy_mdr.exe` + `dist/epy_mdr/_internal/`

The .ico is embedded in the executable via `epy_mdr.spec`.

#### Step 2 — Install Inno Setup

**Option A — winget (unattended):**
```
winget install -e --id JRSoftware.InnoSetup --accept-source-agreements --accept-package-agreements --silent
```

**Option B — direct download:**  
https://jrsoftware.org/isdl.php

#### Step 3 — Compile the installer

```cmd
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\windows\epy_mdr.iss
```

or if system-wide:

```cmd
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer\windows\epy_mdr.iss
```

Output: `installer/dist/epy_mdr-setup-0.4.1.exe`

#### What the Windows installer does

- Per-user install to `%LOCALAPPDATA%\Programs\epy_mdr\` (no UAC prompt)
- Start Menu shortcut; optional Desktop shortcut
- Post-install: runs `epy_mdr.exe --register --as-default` in the current user's context
  - Writes `HKCU\Software\Classes\epy_mdr.Document.1` (ProgID)
  - Writes `HKCU\Software\epy_mdr\Capabilities` + `RegisteredApplications` (appears in Settings)
  - Writes `OpenWithProgids` for `.md`, `.markdown`, `.qmd`
  - Writes the legacy default handler for each extension
- Uninstall: runs `epy_mdr.exe --unregister` to clean up all HKCU keys

#### Windows default-app limitation

Windows 10 and 11 protect file-type defaults with a signed `UserChoice` key
(HMAC-SHA256 with a machine- and user-specific salt) that only the Windows
shell can produce. No installer can silently change this key without triggering
a "A program tried to change your defaults" reset.

The installer writes everything correctly so epy_mdr appears in **Settings >
Apps > Default apps**. The user must then:

1. Open Settings > Apps > Default apps, search for "epy_mdr", and click
   **Set as default**, or
2. Right-click a `.md` file > Open with > Choose another app > epy_mdr >
   Always use this app.

The installer's optional final checkbox ("Open Windows Default Apps settings")
launches `ms-settings:defaultapps` as a convenience shortcut.

---

### 3. Ubuntu .deb

```bash
python installer/linux/build_deb.py
```

Output: `installer/dist/epy-mdr_0.4.1_all.deb`

The script is pure Python (stdlib + pypandoc), runs on Windows or Linux.

#### Install on Ubuntu/Debian

```bash
sudo dpkg -i installer/dist/epy-mdr_0.4.1_all.deb
```

`dpkg -i` is enough — the package's `postinst` pip-installs the Python
runtime deps (PySide6, pypdf, reportlab). Do NOT run `apt-get install -f`:
it is unnecessary here and can hang if another half-configured package on
the system has an interactive `postinst`.

#### What the .deb installs

| Path | Content |
|------|---------|
| `/usr/bin/epy-mdr` | Shell launcher (exec python3 → epy_mdr.app:main) |
| `/usr/lib/epy-mdr/epy_mdr/` | epy_mdr Python package |
| `/usr/lib/epy-mdr/pypandoc/` | pypandoc pure-Python files |
| `/usr/share/applications/epy_mdr.desktop` | Desktop entry (MimeType registered) |
| `/usr/share/mime/packages/epy_mdr.xml` | MIME definition for `text/x-quarto-markdown` |
| `/usr/share/icons/hicolor/256x256/apps/epy_mdr.png` | App icon |

#### postinst actions

1. `update-mime-database /usr/share/mime` — activates `text/x-quarto-markdown`
2. `update-desktop-database /usr/share/applications` — registers the .desktop
3. Appends `text/markdown`, `text/x-markdown`, `text/x-quarto-markdown` entries
   to `/usr/share/applications/defaults.list`

#### Ubuntu default-app semantics and limitation

`/usr/share/applications/defaults.list` is a system-wide hint that GNOME,
XFCE, and LXDE consult when no per-user `mimeapps.list` entry exists. It is
**not** authoritative — each desktop environment makes its own decision.

To set epy_mdr as the personal default for the current user:

```bash
xdg-mime default epy_mdr.desktop text/markdown
xdg-mime default epy_mdr.desktop text/x-markdown
xdg-mime default epy_mdr.desktop text/x-quarto-markdown
```

Or right-click a `.md` file in Nautilus/Thunar → Properties → Open With →
epy_mdr → Set as default.

Note: `xdg-mime` called as `root` in postinst only modifies root's
`~/.config/mimeapps.list`, not individual users' configs. This is standard
Debian packaging behavior.

---

## CI / GitHub Actions

Trigger: `workflow_dispatch` or any `v*` tag push.

Workflow file: `.github/workflows/installers.yml`

| Job | Runner | Output artifact |
|-----|--------|-----------------|
| `windows-installer` | `windows-latest` | `epy_mdr-setup-*.exe` |
| `ubuntu-deb` | `ubuntu-latest` | `epy-mdr_*.deb` |

The Windows CI job uses `choco install innosetup` which is available on
`windows-latest` runners.

---

## Uninstall

### Windows
Use **Settings > Apps > Installed apps** or the Start Menu uninstall entry.
The uninstaller runs `epy_mdr.exe --unregister` which removes all HKCU keys
written during installation.

### Ubuntu / Debian
```bash
sudo dpkg -r epy-mdr
```
The prerm script removes the `defaults.list` entries before package removal.
