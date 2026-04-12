# Installation Guide

This guide covers the supported ways to run LCCN Harvester.

---

## Option 1: Run From Source

### Requirements

- Python 3.10 or newer
- A working internet connection for dependency installation

### Setup

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app_entry.py
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app_entry.py
```

On macOS and Linux you can also launch with:

```bash
./run_gui.sh
```

That helper sets certificate-related environment variables before starting the GUI.

---

## Option 2: Build A Local App Package

Prebuilt binaries are not committed to the repository. Build locally instead:

- macOS: `build_mac.sh`
- Windows: `build_windows.bat`

See [local_app_build_guide.md](local_app_build_guide.md) for the full packaging workflow.

---

## First Run Checklist

1. Open `Configure`.
2. Confirm the active profile and target list look correct.
3. Go to `Harvest`.
4. Load a test input file and verify the preview.
5. Start a small harvest run.

---

## Troubleshooting

### `ModuleNotFoundError` or missing dependency errors

Make sure the virtual environment is active and reinstall dependencies:

```bash
pip install -r requirements.txt
```

### Certificate or SSL errors

```bash
python3 -m pip install --upgrade pip certifi
```

### PowerShell blocks virtual-environment activation

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### PyZ3950 install problems

The project depends on `PyZ3950` from GitHub. If dependency installation fails, retry with network access available and then rerun `pip install -r requirements.txt`.

---

## See Also

- [user_guide.md](user_guide.md)
- [local_app_build_guide.md](local_app_build_guide.md)
- [contribution_guide.md](contribution_guide.md)
