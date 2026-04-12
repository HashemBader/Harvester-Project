# Local App Build Guide

Use this guide to build local macOS or Windows packages from the repository.

The provided scripts expect you to build from the `main` branch and will refuse to continue if you are on a different branch.

---

## Prerequisites

- Python installed
- Project dependencies available
- A clean enough checkout to build from

Optional:

- Set `INSTALL_BUILD_DEPS=1` to let the scripts install packaging dependencies automatically
- Install Inno Setup 6 on Windows if you also want the installer package

---

## macOS

From the project root:

```bash
chmod +x build_mac.sh
INSTALL_BUILD_DEPS=1 ./build_mac.sh
```

Expected outputs:

- `dist/LCCN Harvester.app`
- `dist/LCCN_Harvester.dmg` when DMG creation succeeds

---

## Windows

From Command Prompt or PowerShell:

```bat
set INSTALL_BUILD_DEPS=1
build_windows.bat
```

Expected outputs:

- `dist\LCCN_Harvester.exe`
- `dist\LCCN_Harvester_Setup.exe` when Inno Setup 6 is installed

---

## Notes

- Both scripts call PyInstaller with `LCCN_Harvester.spec`.
- The build scripts clean `build/` and `dist/` before packaging.
- macOS and Windows builds are separate; there is no packaged Linux build script in this repository.

---

## Recommended Workflow

1. Switch to `main`.
2. Pull the latest changes.
3. Ensure dependencies are installed.
4. Run the platform build script.
5. Smoke-test the generated app before sharing it.

---

## See Also

- [installation_guide.md](installation_guide.md)
- [contribution_guide.md](contribution_guide.md)
