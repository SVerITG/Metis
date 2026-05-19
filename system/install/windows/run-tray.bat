@echo off
:: Metis Tray Launcher — Windows
:: Starts Metis in the system tray (no visible terminal window).
:: Use this as the desktop shortcut target after install.

setlocal

set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%..\..") do set "METIS_ROOT=%%~fi"

:: Load env vars from .env
set "ENV_FILE=%METIS_ROOT%\system\.env"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        if not "%%a"=="" if not "%%b"=="" set "%%a=%%b"
    )
)

set "METIS_RC_ROOT=%METIS_ROOT%"
set "PYTHONPATH=%METIS_ROOT%\system\mcp-server\src"

:: Use pythonw.exe so no console window appears
set "PYTHONW=%METIS_ROOT%\system\mcp-server\.venv-win\Scripts\pythonw.exe"
if not exist "%PYTHONW%" (
    set "PYTHONW=%METIS_ROOT%\system\mcp-server\.venv-win\Scripts\python.exe"
)
if not exist "%PYTHONW%" (
    msgbox "Metis: Python environment not found. Please run the installer."
    exit /b 1
)

set "TRAY_SCRIPT=%METIS_ROOT%\system\install\tray_launcher.py"
if not exist "%TRAY_SCRIPT%" (
    msgbox "Metis tray launcher not found: %TRAY_SCRIPT%"
    exit /b 1
)

start "" "%PYTHONW%" "%TRAY_SCRIPT%"
