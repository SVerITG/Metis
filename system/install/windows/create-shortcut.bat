@echo off
:: Metis — Create Desktop Shortcut
:: Double-click this file once to put a Metis shortcut (with icon) on your Desktop.

setlocal

set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%..\..\..") do set "METIS_ROOT=%%~fi"

set "VBS=%SCRIPT_DIR%launch-dashboard-silent.vbs"
set "ICO=%SCRIPT_DIR%metis.ico"
set "SHORTCUT=%USERPROFILE%\Desktop\Metis.lnk"

if not exist "%VBS%" (
    msg * "Could not find Metis launcher. Please re-install Metis."
    exit /b 1
)

powershell.exe -NoProfile -NonInteractive -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath = 'wscript.exe';" ^
  "$s.Arguments = '\"%VBS%\"';" ^
  "$s.WorkingDirectory = '%METIS_ROOT%';" ^
  "$s.IconLocation = '%ICO%,0';" ^
  "$s.Description = 'Open Metis Research Dashboard';" ^
  "$s.Save();"

if exist "%SHORTCUT%" (
    echo Metis shortcut created on your Desktop.
    echo You can close this window.
) else (
    msg * "Could not create shortcut. Please try running as Administrator."
)

timeout /t 3 /nobreak >nul
