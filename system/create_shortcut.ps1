# create_shortcut.ps1
# Creates a Desktop shortcut and Start Menu entry for the Metis Python dashboard.
# Run once:
#   powershell -ExecutionPolicy Bypass -File "create_shortcut.ps1"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatFile   = Join-Path $ScriptDir "launch-metis.bat"
$IcoFile   = Join-Path $ScriptDir "app-py\static\metis.ico"

if (-not (Test-Path $BatFile)) {
    Write-Error "launch-metis.bat not found at: $BatFile"
    exit 1
}

if (Test-Path $IcoFile) {
    Write-Host "Icon found: $IcoFile" -ForegroundColor Cyan
} else {
    Write-Host "Icon not found at: $IcoFile" -ForegroundColor Yellow
    Write-Host "Shortcut will use the default Windows icon instead." -ForegroundColor Yellow
    $IcoFile = $null
}

# Helper to create a shortcut
function New-MetisShortcut {
    param([string]$Path, [string]$Description)
    $Shell = New-Object -ComObject WScript.Shell
    $sc = $Shell.CreateShortcut($Path)
    $sc.TargetPath       = $BatFile
    $sc.WorkingDirectory = $ScriptDir
    $sc.Description      = $Description
    $sc.WindowStyle      = 1
    if ($IcoFile) { $sc.IconLocation = "$IcoFile,0" }
    $sc.Save()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($Shell) | Out-Null
}

# Create shortcuts
$Desktop    = [System.Environment]::GetFolderPath("Desktop")
$DesktopLnk = Join-Path $Desktop "Metis.lnk"
New-MetisShortcut -Path $DesktopLnk -Description "Open Metis Research Dashboard"
Write-Host "Desktop shortcut created." -ForegroundColor Green

$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$StartLnk  = Join-Path $StartMenu "Metis.lnk"
New-MetisShortcut -Path $StartLnk -Description "Open Metis Research Dashboard"
Write-Host "Start Menu shortcut created." -ForegroundColor Green

# Auto-start on Windows login — Metis launches silently when you sign in,
# so the dashboard is always ready at http://localhost:8080.
$Startup    = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$StartupLnk = Join-Path $Startup "Metis.lnk"
New-MetisShortcut -Path $StartupLnk -Description "Auto-start Metis Research Dashboard on login"
Write-Host "Auto-start shortcut created (launches on login)." -ForegroundColor Green

# Course-specific .url shortcut (opens in default browser)
$CourseUrl = "http://127.0.0.1:3000/"
$CourseIco = Join-Path $ScriptDir "app-py\static\course-icon.ico"
if (-not (Test-Path $CourseIco)) {
    Write-Host "Course icon not found at: $CourseIco - using Metis icon" -ForegroundColor Yellow
    $CourseIco = $IcoFile
}

$CourseDesktopLnk = Join-Path $Desktop "Statistics to Multilevel Models.url"
@"
[InternetShortcut]
URL=$CourseUrl
IconIndex=0
$(if ($CourseIco) { "IconFile=$CourseIco" })
"@ | Out-File -Encoding ASCII $CourseDesktopLnk
Write-Host "Course desktop shortcut created: $CourseDesktopLnk" -ForegroundColor Green

$StartCourseLnk = Join-Path $StartMenu "Statistics to Multilevel Models.url"
@"
[InternetShortcut]
URL=$CourseUrl
IconIndex=0
$(if ($CourseIco) { "IconFile=$CourseIco" })
"@ | Out-File -Encoding ASCII $StartCourseLnk
Write-Host "Course Start Menu entry created." -ForegroundColor Green

# Clear Windows icon cache so the new icon appears immediately
Write-Host ""
Write-Host "Refreshing Windows icon cache..." -ForegroundColor Cyan
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800
Remove-Item "$env:LOCALAPPDATA\IconCache.db" -Force -ErrorAction SilentlyContinue
Get-ChildItem "$env:LOCALAPPDATA\Microsoft\Windows\Explorer" -Filter "iconcache_*" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue
Start-Process explorer
Start-Sleep -Milliseconds 1200

Write-Host ""
Write-Host "Done! The Metis shortcut on your Desktop has been updated." -ForegroundColor Green
Write-Host "Dashboard runs on http://127.0.0.1:8080" -ForegroundColor Cyan
