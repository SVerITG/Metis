@echo off
:: Metis MCP Server — Windows launcher (no WSL required)
:: This runs automatically in the background when Claude Desktop uses Metis tools.
:: You do not need to run this manually.

setlocal

:: Locate the Metis root (2 levels up from this script)
set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%..\..\..") do set "METIS_ROOT=%%~fi"

:: Load env vars from .env
set "ENV_FILE=%METIS_ROOT%\system\.env"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        if not "%%a"=="" if not "%%b"=="" set "%%a=%%b"
    )
)

set "METIS_RC_ROOT=%METIS_ROOT%"
set "PYTHONPATH=%METIS_ROOT%\system\mcp-server\src"

:: Find Python in the local venv
set "VENV_PYTHON=%METIS_ROOT%\system\mcp-server\.venv-win\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo Metis MCP server: Python environment not found.
    echo Please run the Metis installer again to set up the tools.
    exit /b 1
)

:: Launch MCP server
"%VENV_PYTHON%" -m metis_mcp.server
