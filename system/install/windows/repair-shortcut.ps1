# repair-shortcut.ps1 - (re)create the Metis shortcuts, hidden and consistent.
#
# Creates BOTH a Desktop shortcut and a Start-menu entry, each pointing at the
# silent launcher (wscript + launch-dashboard-silent.vbs) so NO console window
# ever appears. Uses the high-resolution metis.ico. Idempotent - safe to re-run.
#
# Run by double-clicking, or:  powershell -ExecutionPolicy Bypass -File repair-shortcut.ps1
#
# (Earlier this pointed the shortcut straight at run-dashboard.bat in a VISIBLE
#  window for debugging - that regressed the "no terminal" goal and is undone here.)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot\..\..\..").Path
$vbs  = Join-Path $root 'system\install\windows\launch-dashboard-silent.vbs'
$ico  = Join-Path $root 'system\install\windows\metis.ico'

if (-not (Test-Path $vbs)) { Write-Error "Silent launcher not found: $vbs"; exit 1 }

function New-MetisShortcut($lnkPath) {
    $ws  = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($lnkPath)
    $lnk.TargetPath       = "$env:WINDIR\System32\wscript.exe"  # runs the VBS silently
    $lnk.Arguments        = "`"$vbs`""
    $lnk.WorkingDirectory = $root
    $lnk.WindowStyle      = 1            # the wscript host is windowless anyway
    $lnk.Description       = 'Open the Metis research dashboard'
    if (Test-Path $ico) { $lnk.IconLocation = "$ico,0" }
    $lnk.Save()
    Write-Output "  created: $lnkPath  (hidden launcher, icon: $(Test-Path $ico))"
}

# 1) Desktop
$desktop = [Environment]::GetFolderPath('Desktop')
New-MetisShortcut (Join-Path $desktop 'Metis.lnk')

# 2) Start menu (under a Metis folder so it groups nicely)
$startDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'Metis'
New-Item -ItemType Directory -Force -Path $startDir | Out-Null
New-MetisShortcut (Join-Path $startDir 'Metis.lnk')

Write-Output ""
Write-Output "Done. Metis is on your Desktop and in the Start menu (search 'Metis')."
Write-Output "Both launch hidden - no terminal window."
