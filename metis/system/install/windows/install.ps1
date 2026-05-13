#Requires -Version 5.1
<#
.SYNOPSIS
    Metis Research Cortex — Windows Installer
    Installs Claude Desktop, Python, the MCP server, and the dashboard.
    No WSL. No terminal knowledge required.

.PARAMETER Stage1Only
    Install only the AI assistant (Claude Desktop + Metis persona).
    No dashboard, no MCP server tools. Fastest option (~3 min).

.PARAMETER SkipClaude
    Skip Claude Desktop installation (if already installed).

.PARAMETER SkipPython
    Skip Python installation (if already installed and on PATH).

.PARAMETER InstallDir
    Where to install Metis research files.
    Default: $HOME\Documents\Metis

.PARAMETER ApiKey
    Anthropic API key. If not provided, the installer will prompt.
#>
param(
    [switch]$Stage1Only,
    [switch]$SkipClaude,
    [switch]$SkipPython,
    [string]$InstallDir = "",
    [string]$ApiKey     = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colours & helpers ────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n  ► $msg" -ForegroundColor Cyan  }
function Write-OK    { param($msg) Write-Host "    ✓ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "    ⚠ $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "    ✗ $msg" -ForegroundColor Red; exit 1 }
function Pause-User  { param($msg = "Press Enter to continue…") Read-Host "`n  $msg" | Out-Null }

# ── Banner ───────────────────────────────────────────────────────────────────
Clear-Host
Write-Host @"

  ╔══════════════════════════════════════════════════════════╗
  ║           METIS — Research Cortex Installer              ║
  ║           AI assistant for researchers                   ║
  ╚══════════════════════════════════════════════════════════╝

  This installer will:
    1. Install Claude Desktop (the AI interface)
    2. Install Python (the engine, hidden in the background)
    3. Set up Metis (the research intelligence layer)
    4. Configure everything automatically
    5. Launch Claude Desktop, ready to go

  Nothing requires technical knowledge.
  You only need an Anthropic API key (free to obtain).

"@ -ForegroundColor White

# ── Windows version check ────────────────────────────────────────────────────
Write-Step "Checking Windows version"
$winVer = [System.Environment]::OSVersion.Version
if ($winVer.Major -lt 10 -or ($winVer.Major -eq 10 -and $winVer.Build -lt 17763)) {
    Write-Fail "Metis requires Windows 10 (version 1809) or later. Your version: $winVer"
}
Write-OK "Windows $($winVer.Major).$($winVer.Build)"

# ── Install directory ────────────────────────────────────────────────────────
if (-not $InstallDir) {
    $defaultDir = Join-Path $HOME "Documents\Metis"
    Write-Host "`n  Where would you like to keep your Metis research files?" -ForegroundColor White
    Write-Host "  (Press Enter for default: $defaultDir)" -ForegroundColor Gray
    $userDir = Read-Host "  >"
    $InstallDir = if ($userDir.Trim()) { $userDir.Trim() } else { $defaultDir }
}
$InstallDir = [IO.Path]::GetFullPath($InstallDir)
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Write-OK "Research files will be in: $InstallDir"

# ── API key ──────────────────────────────────────────────────────────────────
if (-not $ApiKey) {
    Write-Host @"

  You need an Anthropic API key to use Metis.
  Get one free at: https://console.anthropic.com

  Your key starts with: sk-ant-...
  It will be stored only on your computer, never shared.

"@ -ForegroundColor White
    $ApiKey = Read-Host "  Paste your Anthropic API key here"
    if (-not $ApiKey.StartsWith("sk-ant-")) {
        Write-Warn "Key doesn't look right (should start with sk-ant-). Continuing anyway."
    }
}

# ── winget availability ──────────────────────────────────────────────────────
Write-Step "Checking package manager"
$hasWinget = $null -ne (Get-Command winget -ErrorAction SilentlyContinue)
if (-not $hasWinget) {
    Write-Warn "winget not found. Will download installers directly instead."
}
else {
    Write-OK "winget available"
}

# ── Install Claude Desktop ───────────────────────────────────────────────────
if (-not $SkipClaude) {
    Write-Step "Installing Claude Desktop"
    $claudeExe = Join-Path $env:LOCALAPPDATA "Programs\Claude\Claude.exe"
    if (Test-Path $claudeExe) {
        Write-OK "Claude Desktop already installed"
    }
    elseif ($hasWinget) {
        Write-Host "    Installing via winget…" -ForegroundColor Gray
        winget install --id Anthropic.Claude --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        if (Test-Path $claudeExe) { Write-OK "Claude Desktop installed" }
        else { Write-Warn "winget install may have failed — check manually at https://claude.ai/download" }
    }
    else {
        Write-Host "    Downloading Claude Desktop installer…" -ForegroundColor Gray
        $claudeInstaller = Join-Path $env:TEMP "ClaudeSetup.exe"
        Invoke-WebRequest -Uri "https://claude.ai/download" -OutFile $claudeInstaller -UseBasicParsing 2>&1 | Out-Null
        Write-Host "    Running installer (follow the prompts)…" -ForegroundColor Gray
        Start-Process -FilePath $claudeInstaller -Wait
        Write-OK "Claude Desktop installed"
    }
}

# ── Install Python ───────────────────────────────────────────────────────────
if (-not $SkipPython -and -not $Stage1Only) {
    Write-Step "Installing Python 3.11"
    $pythonExe = $null
    # Check existing Python
    foreach ($candidate in @("python3.11", "python3", "python")) {
        $found = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($found -and (& $found.Source --version 2>&1) -match "3\.(1[01]|[89])") {
            $pythonExe = $found.Source
            break
        }
    }
    if ($pythonExe) {
        Write-OK "Python already installed: $pythonExe"
    }
    elseif ($hasWinget) {
        winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path","User")
        $pythonExe = (Get-Command python -ErrorAction SilentlyContinue)?.Source
        if ($pythonExe) { Write-OK "Python 3.11 installed" }
        else {
            Write-Warn "Python install via winget may have failed. Trying direct download…"
            $pyInstaller = Join-Path $env:TEMP "python-3.11.9.exe"
            Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" `
                -OutFile $pyInstaller -UseBasicParsing
            Start-Process -FilePath $pyInstaller `
                -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path","User")
            $pythonExe = (Get-Command python -ErrorAction SilentlyContinue)?.Source
        }
    }
    if (-not $pythonExe) { Write-Fail "Python installation failed. Please install Python 3.11 from https://python.org and re-run." }
    Write-OK "Python: $pythonExe"
}

# ── Copy Metis files ─────────────────────────────────────────────────────────
Write-Step "Setting up Metis research files"
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot    = Split-Path -Parent (Split-Path -Parent $scriptDir)  # …/metis/system → …/metis
$metisTarget = Join-Path $InstallDir "metis"

if (-not (Test-Path $metisTarget)) {
    # If running from the repo, copy; otherwise clone from GitHub
    if (Test-Path (Join-Path $repoRoot "agents")) {
        Write-Host "    Copying from installer package…" -ForegroundColor Gray
        Copy-Item -Path $repoRoot -Destination $metisTarget -Recurse -Force
    }
    else {
        Write-Host "    Downloading Metis from GitHub…" -ForegroundColor Gray
        $gitAvail = Get-Command git -ErrorAction SilentlyContinue
        if ($gitAvail) {
            git clone --depth 1 https://github.com/SVerITG/Metis_PH.git $metisTarget 2>&1 | Out-Null
        }
        else {
            $zipPath = Join-Path $env:TEMP "metis.zip"
            Invoke-WebRequest -Uri "https://github.com/SVerITG/Metis_PH/archive/refs/heads/main.zip" `
                -OutFile $zipPath -UseBasicParsing
            Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
            Move-Item -Path (Join-Path $env:TEMP "Metis_PH-main") -Destination $metisTarget -Force
        }
    }
    Write-OK "Metis files ready"
}
else {
    Write-OK "Metis files already present (skipping copy)"
}

# ── Create personal folders ──────────────────────────────────────────────────
foreach ($folder in @("journal", "inbox", "inputs/meetings", "inputs/literature",
                       "projects/active", "outputs/reviews", "archive")) {
    $dir = Join-Path $metisTarget $folder
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}
Write-OK "Personal folders created"

# ── Write .env file ──────────────────────────────────────────────────────────
$envFile = Join-Path $metisTarget "system\.env"
if (-not (Test-Path (Split-Path $envFile))) {
    New-Item -ItemType Directory -Path (Split-Path $envFile) -Force | Out-Null
}
@"
ANTHROPIC_API_KEY=$ApiKey
METIS_RC_ROOT=$metisTarget
"@ | Set-Content -Path $envFile -Encoding UTF8
Write-OK ".env file written (API key stored locally)"

# ── Install MCP server (Stage 2) ─────────────────────────────────────────────
if (-not $Stage1Only) {
    Write-Step "Installing Metis tools (MCP server)"
    $mcpSrc   = Join-Path $metisTarget "system\mcp-server"
    $venvPath = Join-Path $mcpSrc ".venv-win"

    if (-not (Test-Path $venvPath)) {
        Write-Host "    Creating Python environment…" -ForegroundColor Gray
        & $pythonExe -m venv $venvPath 2>&1 | Out-Null
    }

    $pip = Join-Path $venvPath "Scripts\pip.exe"
    Write-Host "    Installing packages (this takes 2–4 minutes)…" -ForegroundColor Gray
    & $pip install --quiet --upgrade pip 2>&1 | Out-Null
    & $pip install --quiet -e (Join-Path $mcpSrc ".") 2>&1 | Out-Null
    & $pip install --quiet "faster-whisper>=1.0" "feedparser>=6.0" "pyzotero>=1.5" 2>&1 | Out-Null
    Write-OK "MCP server packages installed"

    # Write run-mcp.bat
    $runMcpBat = Join-Path $mcpSrc "run-windows.bat"
    @"
@echo off
set "METIS_RC_ROOT=$metisTarget"
set "PYTHONPATH=$mcpSrc\src"
for /f "delims=" %%i in ('type "$metisTarget\system\.env"') do set %%i
"$venvPath\Scripts\python.exe" -m metis_mcp.server
"@ | Set-Content -Path $runMcpBat -Encoding ASCII
    Write-OK "MCP server launcher created"

    # Write run-dashboard.bat
    $dashDir    = Join-Path $metisTarget "system\app-py"
    $runDashBat = Join-Path $dashDir "run-windows.bat"
    @"
@echo off
set "METIS_RC_ROOT=$metisTarget"
set "PYTHONPATH=$mcpSrc\src"
for /f "delims=" %%i in ('type "$metisTarget\system\.env"') do set %%i
cd /d "$dashDir"
"$venvPath\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
"@ | Set-Content -Path $runDashBat -Encoding ASCII
    Write-OK "Dashboard launcher created"
}

# ── Configure Claude Desktop ─────────────────────────────────────────────────
Write-Step "Configuring Claude Desktop"
$claudeConfigDir = Join-Path $env:APPDATA "Claude"
if (-not (Test-Path $claudeConfigDir)) { New-Item -ItemType Directory -Path $claudeConfigDir -Force | Out-Null }
$claudeConfig = Join-Path $claudeConfigDir "claude_desktop_config.json"

if ($Stage1Only) {
    $mcpBlock = "{}"
}
else {
    $mcpSrc   = Join-Path $metisTarget "system\mcp-server"
    $venvPath = Join-Path $mcpSrc ".venv-win"
    $pythonW  = Join-Path $venvPath "Scripts\pythonw.exe"
    $mcpBlock = @"
{
  "metis-rc": {
    "command": "$($pythonW -replace '\\','\\\\')".Replace('"',''),
    "args": ["-m", "metis_mcp.server"],
    "env": {
      "METIS_RC_ROOT": "$($metisTarget -replace '\\','\\\\')".Replace('"',''),
      "PYTHONPATH": "$((Join-Path $mcpSrc 'src') -replace '\\','\\\\')".Replace('"',''),
      "ANTHROPIC_API_KEY": "$ApiKey"
    }
  }
}
"@
}

$claudeConfigJson = @"
{
  "mcpServers": $mcpBlock
}
"@
$claudeConfigJson | Set-Content -Path $claudeConfig -Encoding UTF8
Write-OK "Claude Desktop configured"

# ── Write global CLAUDE.md ───────────────────────────────────────────────────
Write-Step "Setting up Metis AI instructions"
$claudeMdDir = Join-Path $env:USERPROFILE ".claude"
if (-not (Test-Path $claudeMdDir)) { New-Item -ItemType Directory -Path $claudeMdDir -Force | Out-Null }
$claudeMd = Join-Path $claudeMdDir "CLAUDE.md"

# Check if already configured
$firstRunMarker = Join-Path $metisTarget "system\config\.first-run"
New-Item -ItemType File -Path $firstRunMarker -Force | Out-Null

$claudeMdContent = @"
# Metis — Research Cortex

**You are Metis**, the researcher's AI companion, always on, from the first message.
**METIS_RC_ROOT:** $metisTarget

## First-run detection
If the file ``$firstRunMarker`` exists, you MUST enter config wizard mode immediately.
Do not answer any other request. Start the wizard with:

  "Welcome. I'm Metis — your research companion.
   Before we start, I'd like to ask you a few questions so I can set myself up properly for you.
   This takes about 10 minutes. Ready? Let's begin."

Then follow the config wizard in: $metisTarget\system\config\first-run-wizard.md
Delete the marker file at the end of the wizard by calling remove_file("$firstRunMarker").

## Normal operation
Speak plain English. Warm, knowledgeable, never technical jargon.
Route requests to the right specialist. Record all outputs.
Read: $metisTarget\agents\metis\system-prompt.md for full routing logic.

## Opt-out
- One message: start with /direct or plain Claude
- Full session: /metis off (re-enable with /metis on)
"@
$claudeMdContent | Set-Content -Path $claudeMd -Encoding UTF8
Write-OK "CLAUDE.md written to $claudeMd"

# ── Desktop shortcuts ────────────────────────────────────────────────────────
Write-Step "Creating shortcuts"
$desktop = [Environment]::GetFolderPath("Desktop")
$wsh     = New-Object -ComObject WScript.Shell

# Claude Desktop shortcut
$claudeExe = Join-Path $env:LOCALAPPDATA "Programs\Claude\Claude.exe"
if (Test-Path $claudeExe) {
    $sc = $wsh.CreateShortcut((Join-Path $desktop "Metis — Open AI.lnk"))
    $sc.TargetPath       = $claudeExe
    $sc.Description      = "Open Metis in Claude Desktop"
    $sc.WorkingDirectory = $HOME
    $sc.Save()
    Write-OK "Shortcut: Metis — Open AI"
}

# Dashboard shortcut (Stage 2 only)
if (-not $Stage1Only) {
    $dashDir = Join-Path $metisTarget "system\app-py"
    $sc2 = $wsh.CreateShortcut((Join-Path $desktop "Metis — Dashboard.lnk"))
    $sc2.TargetPath       = Join-Path $dashDir "run-windows.bat"
    $sc2.Description      = "Open Metis Dashboard in browser"
    $sc2.WindowStyle      = 7  # minimized
    $sc2.Save()
    Write-OK "Shortcut: Metis — Dashboard"
}

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host @"

  ╔══════════════════════════════════════════════════════════╗
  ║                  Installation complete!                  ║
  ╚══════════════════════════════════════════════════════════╝

  What to do next:
    1. Double-click  "Metis — Open AI"  on your desktop
    2. Start typing — Metis will guide you through setup
       (takes about 10 minutes the first time)

  Your research files are in:
    $InstallDir

  To open the dashboard later:
    Double-click  "Metis — Dashboard"  on your desktop

"@ -ForegroundColor Green

# Launch Claude Desktop
$claudeExe = Join-Path $env:LOCALAPPDATA "Programs\Claude\Claude.exe"
if (Test-Path $claudeExe) {
    $launch = Read-Host "  Launch Claude Desktop now? (Y/n)"
    if ($launch -ne "n" -and $launch -ne "N") {
        Start-Process -FilePath $claudeExe
        Write-Host "`n  Claude Desktop is opening. Start typing to begin setup.`n" -ForegroundColor Cyan
    }
}
