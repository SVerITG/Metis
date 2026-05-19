# create_shortcuts.ps1 — Install Metis dashboard shortcuts on Desktop and Start Menu
# Run once from PowerShell (right-click > Run with PowerShell), or from a terminal:
#   powershell -ExecutionPolicy Bypass -File create_shortcuts.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BatchFile = Join-Path $ScriptDir "launch_metis.bat"
$IconFile  = $BatchFile  # use .bat icon fallback (no custom .ico needed)

if (-not (Test-Path $BatchFile)) {
    Write-Error "launch_metis.bat not found in: $ScriptDir"
    exit 1
}

$WshShell = New-Object -ComObject WScript.Shell

function New-Shortcut {
    param($TargetPath, $ShortcutPath, $Description, $WorkingDir)
    $link = $WshShell.CreateShortcut($ShortcutPath)
    $link.TargetPath    = $TargetPath
    $link.WorkingDirectory = $WorkingDir
    $link.Description   = $Description
    $link.WindowStyle   = 1  # Normal window
    $link.Save()
    Write-Host "Created: $ShortcutPath"
}

# Desktop shortcut
$Desktop = [Environment]::GetFolderPath("Desktop")
$DesktopLnk = Join-Path $Desktop "Metis Dashboard.lnk"
New-Shortcut -TargetPath $BatchFile `
             -ShortcutPath $DesktopLnk `
             -Description "Open the Metis Research Dashboard" `
             -WorkingDir $ScriptDir

# Start Menu shortcut
$StartMenu = [Environment]::GetFolderPath("StartMenu")
$ProgramsDir = Join-Path $StartMenu "Programs"
$MetisDir = Join-Path $ProgramsDir "Metis"
if (-not (Test-Path $MetisDir)) { New-Item -ItemType Directory -Path $MetisDir | Out-Null }
$StartLnk = Join-Path $MetisDir "Metis Dashboard.lnk"
New-Shortcut -TargetPath $BatchFile `
             -ShortcutPath $StartLnk `
             -Description "Open the Metis Research Dashboard" `
             -WorkingDir $ScriptDir

Write-Host ""
Write-Host "Done. Shortcuts created:"
Write-Host "  Desktop:    $DesktopLnk"
Write-Host "  Start Menu: $StartLnk"
Write-Host ""
Write-Host "Double-click 'Metis Dashboard' on your desktop to launch."
