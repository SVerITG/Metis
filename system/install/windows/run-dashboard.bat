@echo off
:: Metis Dashboard — Windows launcher
:: Double-click this file to start Metis and open it in your browser.
:: No terminal knowledge required.

setlocal

set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%..\..\..") do set "METIS_ROOT=%%~fi"

:: Check WSL is available
wsl --status >nul 2>&1
if errorlevel 1 (
    msg * "Metis requires WSL (Windows Subsystem for Linux). Please run the Metis installer first."
    exit /b 1
)

:: Convert Windows path to WSL path
for /f "delims=" %%i in ('wsl wslpath -u "%METIS_ROOT%"') do set "WSL_ROOT=%%i"

if "%WSL_ROOT%"=="" (
    msg * "Could not locate the Metis folder in WSL. Please re-run the Metis installer."
    exit /b 1
)

:: Kill any old instance silently
wsl -e bash -c "pkill -f 'uvicorn main:app.*8080' 2>/dev/null; sleep 0.3" >nul 2>&1

:: Start the dashboard in the background (WSL window hidden via vbs wrapper)
start "" /b wsl -e bash "%WSL_ROOT%/system/app-py/run.sh"

:: Wait for run.sh to write the port file, then open browser on the correct port
timeout /t 5 /nobreak >nul
set "PORT=8080"
if exist "%METIS_ROOT%\system\app-py\.metis-port" (
    for /f %%p in (%METIS_ROOT%\system\app-py\.metis-port) do set "PORT=%%p"
)
start "" "http://127.0.0.1:%PORT%"
