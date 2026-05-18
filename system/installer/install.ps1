#Requires -Version 5.1
<#
.SYNOPSIS
    Metis Research Cortex — Windows Installer
.DESCRIPTION
    Installs Metis on Windows with WSL.
    - Checks prerequisites (WSL, Python)
    - Sets up the MCP server in a local Python venv
    - Registers Metis with Claude Code and Claude Desktop
    - Creates Desktop and Start Menu shortcuts
    - Launches the configuration wizard
.NOTES
    Run as your normal user (not Administrator) unless WSL needs installing.
    If WSL is not yet installed, the script will prompt for admin rights just
    for that step, then continue without elevation.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colours ──────────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  [X]  $msg" -ForegroundColor Red }
function Write-Head  { param($msg) Write-Host "`n$msg`n$('-' * $msg.Length)" -ForegroundColor White }

Write-Host @"

  ╔══════════════════════════════════════════════════════╗
  ║          Metis Research Cortex — Installer           ║
  ╚══════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# ── Resolve paths ─────────────────────────────────────────────────────────────
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$MetisRoot   = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path   # metis/
$SetupScript = Join-Path $MetisRoot "system\mcp-server\setup-mcp.sh"
$BatchFile   = Join-Path $MetisRoot "system\launch-metis.bat"
$InitDbScript = Join-Path $ScriptDir "init_db.py"

Write-Head "Step 1 — Checking prerequisites"

# ── WSL ──────────────────────────────────────────────────────────────────────
Write-Step "Checking WSL..."
$wslCheck = wsl --status 2>&1
if ($LASTEXITCODE -ne 0 -or $wslCheck -match "not installed") {
    Write-Warn "WSL is not installed. Installing now (requires restart)..."
    Start-Process "wsl" "--install" -Verb RunAs -Wait
    Write-Warn "WSL installed. Please RESTART your computer, then run this installer again."
    Read-Host "Press Enter to exit"
    exit 0
}
Write-OK "WSL found"

# ── Python in WSL ─────────────────────────────────────────────────────────────
Write-Step "Checking Python in WSL..."
$pyVer = wsl python3 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Step "Installing Python 3.12 in WSL..."
    wsl bash -c "sudo apt-get update -q && sudo apt-get install -y python3.12 python3.12-venv python3-pip"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Could not install Python. Please install Python 3.10+ in WSL manually."
        exit 1
    }
}
Write-OK "Python: $pyVer"

# ── Claude Desktop ────────────────────────────────────────────────────────────
$ClaudeDesktopConfig = "$env:APPDATA\Claude\claude_desktop_config.json"
$ClaudeDesktopFound  = Test-Path $ClaudeDesktopConfig
if (-not $ClaudeDesktopFound) {
    Write-Warn "Claude Desktop not found at $ClaudeDesktopConfig"
    Write-Warn "Install Claude Desktop from https://claude.ai/download then re-run this installer to register."
} else {
    Write-OK "Claude Desktop found"
}

Write-Head "Step 2 — Installing MCP server"

# Convert Windows path to WSL path for the setup script
$SetupScriptWSL = wsl wslpath -u $SetupScript.Replace('\', '/')
Write-Step "Running: $SetupScript"
wsl bash "$SetupScriptWSL"
if ($LASTEXITCODE -ne 0) {
    Write-Fail "MCP server setup failed. Check the output above."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-OK "MCP server installed and registered"

Write-Head "Step 3 — Initializing database"

$DbPath = Join-Path $MetisRoot "system\app\data\metis.sqlite"
if (-not (Test-Path $DbPath)) {
    Write-Step "Creating metis.sqlite..."
    $InitDbWSL = wsl wslpath -u $InitDbScript.Replace('\', '/')
    wsl python3 "$InitDbWSL"
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Database created"
    } else {
        Write-Warn "Database init failed — dashboard will show empty data on first run"
    }
} else {
    Write-OK "Database already exists"
}

Write-Head "Step 4 — Creating shortcuts"

$WShell = New-Object -ComObject WScript.Shell

# Generate the .bat launcher if it doesn't exist yet
if (-not (Test-Path $BatchFile)) {
    $BatchFileWSL = wsl wslpath -u $BatchFile.Replace('\', '/')
    $RunSh        = Join-Path $MetisRoot "system\app-py\run.sh"
    $RunShWSL     = wsl wslpath -u $RunSh.Replace('\', '/')
    $BatContent   = "@echo off`r`ntitle Metis -- Starting...`r`nstart `"Metis Dashboard`" wsl.exe -e bash `"$RunShWSL`"`r`ntimeout /t 6 /nobreak > nul`r`nstart `"`" `"http://127.0.0.1:8080`"`r`nexit"
    Set-Content -Path $BatchFile -Value $BatContent -Encoding ASCII
}

foreach ($Dest in @(
    [System.Environment]::GetFolderPath('Desktop') + "\Metis.lnk",
    [System.Environment]::GetFolderPath('Programs') + "\Metis.lnk"
)) {
    $sc = $WShell.CreateShortcut($Dest)
    $sc.TargetPath       = $BatchFile
    $sc.WorkingDirectory = Split-Path $BatchFile
    $sc.Description      = "Metis Research Cortex Dashboard"
    $sc.WindowStyle      = 1
    $sc.Save()
    Write-OK "Shortcut: $Dest"
}

Write-Head "Step 5 — Done"

Write-Host @"

  Metis is installed.

  NEXT STEPS:
  ------------------------------------------------------
  1. Restart Claude Desktop and Claude Code
     (required for the MCP server to appear)

  2. Open Claude Code in this folder and run:
       /metis_config
     This walks you through personalising Metis for
     your research domain, projects, and preferences.

  3. Connect your reference library:
       /metis-library-setup

  4. Double-click the Metis shortcut on your Desktop
     to open the dashboard.
  ------------------------------------------------------

"@ -ForegroundColor Green

exit 0
