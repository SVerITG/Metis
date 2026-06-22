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

:: Do NOT kill a running instance here. run.sh now owns the singleton: it ADOPTS a
:: healthy dashboard (and only clears a wedged one). Killing a healthy server mid-
:: write is what corrupted the DB on 2026-06-19. Safe to double-click repeatedly.

:: Start the dashboard DETACHED so it survives this launcher window closing.
:: setsid + nohup put uvicorn in its own session — closing the console (or the
:: parent process exiting) no longer sends SIGHUP and kills the server.
wsl -e bash -c "setsid nohup bash '%WSL_ROOT%/system/app-py/run.sh' </dev/null >/tmp/metis-dashboard.log 2>&1 & disown" >nul 2>&1

:: Wait for the port file — run.sh writes it once it has chosen a port. If the
:: file doesn't appear within 12 seconds, fall back to 8080.
set "PORT=8080"
for /l %%i in (1,1,12) do (
    if exist "%METIS_ROOT%\system\app-py\.metis-port" (
        for /f %%p in (%METIS_ROOT%\system\app-py\.metis-port) do set "PORT=%%p"
        goto :have_port
    )
    timeout /t 1 /nobreak >nul
)
:have_port
set "URL=http://127.0.0.1:%PORT%"

:: Metis's first start can take 10-30s (it loads the agents, scheduler, and
:: embedding model). Poll the /health endpoint until the dashboard actually
:: responds before opening the browser — a fixed wait used to open it too
:: early and show "can't connect".
:: curl.exe ships with Windows 10 1803+ (our minimum).
for /l %%i in (1,1,60) do (
    curl -s -o nul -m 2 "%URL%/health" && goto :ready
    timeout /t 1 /nobreak >nul
)
:: After 60s, open the browser anyway — user can manually refresh.
:ready
start "" "%URL%"
