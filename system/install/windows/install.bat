@echo off
:: Metis Research Cortex — Windows Installer
:: Double-click this file to install Metis.
:: No technical knowledge required.

echo.
echo  Starting Metis installer...
echo.

:: Check PowerShell availability
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo  Error: PowerShell is not available on this computer.
    echo  Please install PowerShell from https://aka.ms/install-powershell
    pause
    exit /b 1
)

:: Run the installer with unrestricted execution policy for this session only
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*

if %errorlevel% neq 0 (
    echo.
    echo  Installation encountered an issue.
    echo  Please take a screenshot of this window and contact support.
    pause
)
