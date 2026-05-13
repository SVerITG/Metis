@echo off
:: Metis Dashboard — Windows launcher
:: Double-click to open the Metis research dashboard in your browser.

setlocal

set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%..\..\..") do set "METIS_ROOT=%%~fi"

:: Load env vars
set "ENV_FILE=%METIS_ROOT%\system\.env"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        if not "%%a"=="" if not "%%b"=="" set "%%a=%%b"
    )
)

set "METIS_RC_ROOT=%METIS_ROOT%"
set "PYTHONPATH=%METIS_ROOT%\system\mcp-server\src"

set "VENV_PYTHON=%METIS_ROOT%\system\mcp-server\.venv-win\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo Metis dashboard: Python environment not found.
    echo Please run the Metis installer to set up the dashboard.
    pause
    exit /b 1
)

:: Open browser after a short delay
start "" timeout /t 3 /nobreak >nul && start "" "http://127.0.0.1:8000"

:: Launch dashboard
cd /d "%METIS_ROOT%\system\app-py"
"%VENV_PYTHON%" -m uvicorn app:app --host 127.0.0.1 --port 8000
