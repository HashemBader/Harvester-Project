@echo off
:: =============================================================================
:: build_windows.bat  -  Build a Windows .exe and local installer for LCCN Harvester
:: =============================================================================
:: Requirements:
::   - Run from the main branch
::   - Python with project dependencies already installed
::   - Optional: set INSTALL_BUILD_DEPS=1 to let the script try pip installs
::   - Optional: Inno Setup 6 to create the installer (.exe setup)
::
:: Output:
::   dist\LCCN_Harvester.exe         <- portable executable
::   dist\LCCN_Harvester_Setup.exe   <- installer executable (if Inno Setup is installed)
::
:: Usage:
::   Double-click build_windows.bat  -or-  run from a command prompt:
::   build_windows.bat
:: =============================================================================
setlocal enabledelayedexpansion

set "APP_NAME=LCCN Harvester"
set "EXPECTED_BRANCH=main"
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo   LCCN Harvester - Windows Build
echo ========================================

:: ---------------------------------------------------------------------------
:: 0. Ensure we are building from main
:: ---------------------------------------------------------------------------
where git >nul 2>&1
if not errorlevel 1 (
    for /f "usebackq delims=" %%b in (`git branch --show-current 2^>nul`) do set "CURRENT_BRANCH=%%b"
    if defined CURRENT_BRANCH (
        if /i not "!CURRENT_BRANCH!"=="%EXPECTED_BRANCH%" (
            echo [ERROR] Refusing to build from branch "!CURRENT_BRANCH!".
            echo         Switch to "%EXPECTED_BRANCH%" first.
            pause
            exit /b 1
        )
        echo [OK] Building from git branch !CURRENT_BRANCH!
    )
)

:: ---------------------------------------------------------------------------
:: 1. Detect Python
:: ---------------------------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    where python3 >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Please install Python 3.11+ from https://python.org
        echo         Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
    set "PYTHON=python3"
) else (
    set "PYTHON=python"
)

for /f "tokens=*" %%v in ('!PYTHON! --version 2^>^&1') do set PY_VER=%%v
echo [OK] Using !PY_VER!

:: ---------------------------------------------------------------------------
:: 2. Install / upgrade build tools
:: ---------------------------------------------------------------------------
echo.
if /i "%INSTALL_BUILD_DEPS%"=="1" (
    echo [INFO] Installing build dependencies ...
    !PYTHON! -m pip install --quiet --upgrade pip
    !PYTHON! -m pip install --quiet --upgrade pyinstaller pyinstaller-hooks-contrib

    if exist requirements.txt (
        !PYTHON! -m pip install --quiet -r requirements.txt
        if errorlevel 1 (
            echo [WARN] Some requirements failed - trying core packages only ...
            !PYTHON! -m pip install --quiet ^
                "PyQt6>=6.4.0" ^
                "requests>=2.28.0" ^
                "python-stdnum>=2.2" ^
                pymarc ply certifi
        )
    )
) else (
    echo [INFO] Using installed build dependencies. Set INSTALL_BUILD_DEPS=1 to auto-install.
)

for %%m in (PyInstaller PyQt6 requests pymarc certifi) do (
    !PYTHON! -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('%%m') else 1)"
    if errorlevel 1 (
        echo [ERROR] Missing Python module: %%m
        echo         Install dependencies first, or rerun with INSTALL_BUILD_DEPS=1
        pause
        exit /b 1
    )
)

:: ---------------------------------------------------------------------------
:: 3. Clean previous build artefacts
:: ---------------------------------------------------------------------------
echo.
echo [INFO] Cleaning previous build ...
if exist build   rd /s /q build
if exist dist    rd /s /q dist

:: ---------------------------------------------------------------------------
:: 4. Run PyInstaller
:: ---------------------------------------------------------------------------
echo.
echo [INFO] Running PyInstaller ...
!PYTHON! -m PyInstaller --noconfirm --clean LCCN_Harvester.spec

:: ---------------------------------------------------------------------------
:: 5. Verify output
:: ---------------------------------------------------------------------------
if exist "dist\LCCN_Harvester.exe" (
    echo.
    echo [SUCCESS] Build complete!
    echo    Executable: %SCRIPT_DIR%dist\LCCN_Harvester.exe
) else (
    echo.
    echo [ERROR] Build failed - LCCN_Harvester.exe not found in dist\
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------------
:: 6. Optional: build installer with Inno Setup
:: ---------------------------------------------------------------------------
set "ISCC_EXE="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if defined ISCC_EXE (
    echo.
    echo [INFO] Building installer with Inno Setup ...
    "%ISCC_EXE%" "installer_windows.iss"
    if exist "dist\LCCN_Harvester_Setup.exe" (
        echo [SUCCESS] Installer created: %SCRIPT_DIR%dist\LCCN_Harvester_Setup.exe
    ) else (
        echo [WARN] Inno Setup ran, but installer output was not found.
    )
) else (
    echo.
    echo [WARN] Inno Setup 6 was not found.
    echo        Portable exe is ready at dist\LCCN_Harvester.exe
    echo        To build the installer, install Inno Setup 6 and rerun this script.
)

echo ========================================
echo   Done!
echo ========================================
pause
