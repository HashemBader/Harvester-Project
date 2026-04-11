# Local App Build Guide

This guide explains how to create a local desktop app from the repository on:
- macOS
- Windows

This workflow is meant to match the `main` branch.

Why this is the recommended approach:
- A committed `.app` or `.exe` will go out of date unless it is rebuilt after every code change.
- macOS and Windows need different build outputs.
- Rebuilding from `main` gives you an app that reflects the current repository state without storing generated binaries in git.

The repository already includes build scripts for both platforms:
- macOS: `build_mac.sh`
- Windows: `build_windows.bat`

---

## Always Build From `main`

Before creating a local app, make sure your checkout matches the latest `main` branch:

```bash
git checkout main
git pull origin main
```

The existing build scripts are already written to expect `main`.

---

## Prerequisites

You will need:
- A clone or fork of this repository
- Python 3.11 or newer
- Project dependencies installed

macOS / Linux setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell setup:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If packaging tools are missing, the build scripts can install them automatically when run with `INSTALL_BUILD_DEPS=1`.

---

## macOS App

From the project root:

```bash
chmod +x build_mac.sh
INSTALL_BUILD_DEPS=1 ./build_mac.sh
```

Expected output:
- `dist/LCCN Harvester.app`
- `dist/LCCN_Harvester.dmg` when disk image creation succeeds

To run the generated app:

```bash
open "dist/LCCN Harvester.app"
```

To update the app later:

```bash
git checkout main
git pull origin main
INSTALL_BUILD_DEPS=1 ./build_mac.sh
```

This rebuilds the app from the latest `main` branch code.

---

## Windows App

Open Command Prompt or PowerShell in the project root and run:

```bat
set INSTALL_BUILD_DEPS=1
build_windows.bat
```

Expected output:
- `dist\LCCN_Harvester.exe`
- `dist\LCCN_Harvester_Setup.exe` if Inno Setup 6 is installed

To run the generated app:
- Double-click `dist\LCCN_Harvester.exe`

To update the app later:

```bat
git checkout main
git pull origin main
set INSTALL_BUILD_DEPS=1
build_windows.bat
```

This rebuilds the executable from the latest `main` branch code.

---

## Linux

Linux users can continue running the project from the terminal instead of building a packaged desktop app.

---

## Recommended Team Workflow

1. Switch to `main`.
2. Pull the latest changes from `origin/main`.
3. Rebuild the app for your platform.
4. Use the newly generated output from `dist/`.

That keeps the local app aligned with the repository's `main` branch.
