# launch-dashboard.ps1
# Starts the Metis dashboard silently — no visible console window.
# Used by the desktop shortcut. Works on Windows 10/11 and Windows Sandbox.

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $dir "run-dashboard.bat"

if (Test-Path $bat) {
    Start-Process "cmd.exe" -ArgumentList "/c `"$bat`"" -WindowStyle Hidden
} else {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Metis dashboard launcher not found.`n`nExpected:`n$bat`n`nPlease reinstall Metis from:`nhttps://github.com/SVerITG/Metis_PH/releases",
        "Metis — Launcher Error",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error)
}
