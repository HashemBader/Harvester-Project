#!/usr/bin/env bash
# =============================================================================
# build_mac.sh  –  Build a self-contained macOS .app + .dmg for LCCN Harvester
# =============================================================================
# Requirements:
#   - Run this script from the main branch
#   - Python with the project dependencies already installed
#   - Optional: set INSTALL_BUILD_DEPS=1 to let the script try pip installs
#
# Output:
#   dist/LCCN Harvester.app   ← macOS application bundle
#   dist/LCCN_Harvester.dmg   ← distributable disk image
#
# Usage:
#   chmod +x build_mac.sh
#   ./build_mac.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="LCCN Harvester"
DIST_DIR="$SCRIPT_DIR/dist"
BUILD_DIR="$SCRIPT_DIR/build"
PYI_CACHE_DIR="$SCRIPT_DIR/.pyinstaller"
EXPECTED_BRANCH="main"

require_python_module() {
    local module="$1"
    if "$PYTHON" - <<PY >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("$module") else 1)
PY
    then
        return 0
    fi
    return 1
}

echo "========================================"
echo "  LCCN Harvester – macOS Build"
echo "========================================"

# ---------------------------------------------------------------------------
# 1. Detect Python
# ---------------------------------------------------------------------------
PYTHON=$(command -v python3 || command -v python)
if [[ -z "$PYTHON" ]]; then
    echo "❌  Python 3 not found. Please install Python 3.11+ and re-run."
    exit 1
fi
PY_VER=$("$PYTHON" --version 2>&1)
echo "✅  Using $PY_VER at $(command -v "$PYTHON")"

# ---------------------------------------------------------------------------
# 1b. Ensure we are building from main
# ---------------------------------------------------------------------------
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || true)"
    if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
        echo "❌  Refusing to build from branch '$CURRENT_BRANCH'. Switch to '$EXPECTED_BRANCH' first."
        exit 1
    fi
    echo "✅  Building from git branch: $CURRENT_BRANCH"
fi

# ---------------------------------------------------------------------------
# 2. Install / upgrade build tools
# ---------------------------------------------------------------------------
echo ""
if [[ "${INSTALL_BUILD_DEPS:-0}" == "1" ]]; then
    echo "📦  Installing build dependencies …"
    "$PYTHON" -m pip install --quiet --upgrade pip
    "$PYTHON" -m pip install --quiet --upgrade \
        pyinstaller \
        pyinstaller-hooks-contrib

    if [[ -f requirements.txt ]]; then
        "$PYTHON" -m pip install --quiet -r requirements.txt || \
        "$PYTHON" -m pip install --quiet \
            "PyQt6>=6.4.0" \
            "requests>=2.28.0" \
            "python-stdnum>=2.2" \
            pymarc \
            ply \
            certifi
    fi
else
    echo "📦  Using installed build dependencies (set INSTALL_BUILD_DEPS=1 to auto-install)."
fi

for module in PyInstaller PyQt6 requests pymarc certifi; do
    if ! require_python_module "$module"; then
        echo "❌  Missing Python module: $module"
        echo "    Install dependencies first, or rerun with INSTALL_BUILD_DEPS=1"
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# 3. Clean previous build artefacts
# ---------------------------------------------------------------------------
echo ""
echo "🧹  Cleaning previous build …"
python3 - <<PY
import shutil
from pathlib import Path
for path in (Path(r"$BUILD_DIR"), Path(r"$DIST_DIR")):
    if path.exists():
        shutil.rmtree(path)
PY
mkdir -p "$PYI_CACHE_DIR"

# ---------------------------------------------------------------------------
# 4. Run PyInstaller
# ---------------------------------------------------------------------------
echo ""
echo "🔨  Running PyInstaller …"
export PYINSTALLER_CONFIG_DIR="$PYI_CACHE_DIR"
"$PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    LCCN_Harvester.spec

# ---------------------------------------------------------------------------
# 5. Verify output
# ---------------------------------------------------------------------------
APP_PATH="$DIST_DIR/$APP_NAME.app"
if [[ -d "$APP_PATH" ]]; then
    echo ""
    echo "✅  Build succeeded!"
    echo "    App:  $APP_PATH"
    echo ""
    echo "    To run: open \"$APP_PATH\""
else
    echo ""
    echo "❌  Build failed – $APP_NAME.app not found in $DIST_DIR"
    exit 1
fi

# ---------------------------------------------------------------------------
# 6. Optional: create a .dmg disk image
# ---------------------------------------------------------------------------
if command -v hdiutil &>/dev/null; then
    DMG_PATH="$DIST_DIR/LCCN_Harvester.dmg"
    echo "💿  Creating disk image: $DMG_PATH"
    rm -f "$DMG_PATH"
    hdiutil create \
        -volname "$APP_NAME" \
        -srcfolder "$APP_PATH" \
        -ov \
        -format UDZO \
        "$DMG_PATH" \
        2>/dev/null && echo "✅  DMG created: $DMG_PATH" \
                    || echo "⚠️   DMG creation skipped (non-fatal)."
fi

echo ""
echo "========================================"
echo "  Done!  Distribute:"
echo "    • $APP_NAME.app  (drag to Applications)"
if [[ -f "$DIST_DIR/LCCN_Harvester.dmg" ]]; then
echo "    • LCCN_Harvester.dmg  (share this file)"
fi
echo "========================================"
