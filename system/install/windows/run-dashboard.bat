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

:: Give run.sh a moment to choose a port and write the port file.
timeout /t 3 /nobreak >nul
set "PORT=8080"
if exist "%METIS_ROOT%\system\app-py\.metis-port" (
    for /f %%p in (%METIS_ROOT%\system\app-py\.metis-port) do set "PORT=%%p"
)
set "URL=http://127.0.0.1:%PORT%"

:: Metis's first start can take 10-30s (it loads the agents, scheduler, and
:: embedding model). Poll until the dashboard actually responds before opening
:: the browser — a fixed wait used to open it too early and show "can't connect".
:: curl.exe ships with Windows 10 1803+ (our minimum).
for /l %%i in (1,1,40) do (
    curl -s -o nul -m 1 "%URL%" && goto :ready
    timeout /t 1 /nobreak >nul
)
:ready
start "" "%URL%"
