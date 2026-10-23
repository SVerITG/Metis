#Requires -Version 5.1
<#
.SYNOPSIS
    Metis — Windows installer. Native: no WSL, no administrator rights.

.DESCRIPTION
    Sets up the Metis tools (MCP server) in their own Python environment,
    connects them to Claude Desktop and Claude Code, and — unless -Stage1Only —
    installs the research dashboard. Run by MetisSetup.exe, or on its own:

        powershell -ExecutionPolicy Bypass -File install.ps1

    Written for Windows PowerShell 5.1, which is what powershell.exe is on every
    Windows 10 and 11 machine. The previous version used PowerShell 7 syntax and
    could not even be parsed there. Saved as UTF-8 WITH a byte-order mark: 5.1
    reads a file without one in the ANSI code page, where the last byte of an
    em dash is a curly closing quote that ends the string it sits in.

.PARAMETER Stage1Only
    AI only: the Metis tools for Claude, without the dashboard. (Before, this
    connected nothing at all.)
.PARAMETER FromInstaller
    Set by MetisSetup.exe: never prompt, never pause, leave the dashboard
    shortcuts to the setup program.
.PARAMETER DesktopShortcut
    Put "Metis — Open AI" (opens Claude Desktop) on the desktop.
.PARAMETER StartMenuShortcut
    Put "Metis — Open AI" in the Start menu.
.PARAMETER SkipClaude
    Do not install Claude Desktop if it is missing.
.PARAMETER SkipPython
    Accepted for compatibility; Python is now provided by uv either way.
.PARAMETER InstallDir
    The Metis folder. Default: Documents\Metis.
.PARAMETER ApiKey
    Anthropic API key. Optional: Claude Desktop and Claude Code do not need one.
#>
param(
    [switch]$Stage1Only,
    [switch]$FromInstaller,
    [switch]$DesktopShortcut,
    [switch]$StartMenuShortcut,
    [switch]$SkipClaude,
    [switch]$SkipPython,
    [string]$InstallDir = "",
    [string]$ApiKey     = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$interactive = -not $FromInstaller -and [Environment]::UserInteractive

# The extras every installer adds by default; the same list as setup-mcp.sh.
# voice is left out: it compiles C, and a laptop without a compiler failed.
$Extras = "embedding,library,ocr"
$PythonVersion = "3.12"   # pyproject.toml: >=3.10,<3.14

function Write-Step { param($msg) Write-Host "`n  > $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "    ✓ $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    ! $msg" -ForegroundColor Yellow }
function Write-Fail {
    param($msg)
    Write-Host "    ✗ $msg" -ForegroundColor Red
    if ($script:LogFile) { Write-Host "      Details: $script:LogFile" -ForegroundColor Gray }
    if ($interactive) { Read-Host "`n  Press Enter to close" | Out-Null }
    exit 1
}

# Run a native program, send everything it prints to the log, return its exit
# code. In Windows PowerShell 5.1 a native program's stderr line becomes an error
# record, and with ErrorActionPreference=Stop the FIRST progress line uv or pip
# writes to stderr would end the script. So: Continue for the call, and judge
# success by the exit code — the only thing that actually means failure.
function Invoke-Logged {
    param([string]$Exe, [string[]]$Arguments)
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        "`n>> $Exe $($Arguments -join ' ')" | Add-Content -Path $script:LogFile -Encoding UTF8
        & $Exe @Arguments 2>&1 | ForEach-Object { "$_" } |
            Add-Content -Path $script:LogFile -Encoding UTF8
        return $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $old
    }
}

# Add or replace KEY=value in a .env file, keeping every other line. An empty
# value changes nothing: re-running setup without a key must not erase one.
function Set-EnvValue {
    param([string]$File, [string]$Key, [string]$Value)
    if (-not $Value) { return }
    $lines = @()
    if (Test-Path $File) { $lines = @(Get-Content -Path $File -Encoding UTF8) }
    $lines = @($lines | Where-Object { $_ -notmatch "^\s*$([regex]::Escape($Key))=" })
    $lines += "$Key=$Value"
    [IO.File]::WriteAllLines($File, [string[]]$lines, (New-Object Text.UTF8Encoding($false)))
}

# Where Claude Desktop is, as something a shortcut can open. The Microsoft
# Store edition has no fixed .exe path at all — it is opened through its
# Start-menu entry — so both editions are looked for.
function Find-ClaudeDesktop {
    foreach ($p in @(
            (Join-Path $env:LOCALAPPDATA "AnthropicClaude\claude.exe"),
            (Join-Path $env:LOCALAPPDATA "Programs\Claude\Claude.exe"),
            (Join-Path $env:ProgramFiles "Anthropic\Claude\Claude.exe"))) {
        if (Test-Path $p) { return @{ Target = $p; Arguments = "" } }
    }
    try {
        # Get-StartApps (Windows 10+) takes no -ErrorAction in 5.1; the try covers it.
        $app = Get-StartApps |
            Where-Object { $_.Name -eq "Claude" -or $_.AppID -like "Claude_*" } |
            Select-Object -First 1
        if ($app) {
            return @{ Target = "$env:WINDIR\explorer.exe"; Arguments = "shell:AppsFolder\$($app.AppID)" }
        }
    }
    catch { }
    return $null
}

function New-Shortcut {
    param([string]$Path, [string]$Target, [string]$Arguments = "",
          [string]$Icon = "", [string]$Description = "")
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($Path)
    $sc.TargetPath = $Target
    if ($Arguments)   { $sc.Arguments   = $Arguments }
    if ($Icon)        { $sc.IconLocation = "$Icon,0" }
    if ($Description) { $sc.Description = $Description }
    $sc.Save()
}

# ── Banner ───────────────────────────────────────────────────────────────────
if ($interactive) {
    Write-Host @"

  Metis — research companion for Claude

  This sets up:
    1. The Metis tools, in their own Python environment
    2. The connection to Claude Desktop (and Claude Code, if you use it)
    3. The research dashboard (unless you chose AI only)

  Nothing here needs technical knowledge, and nothing needs administrator rights.

"@ -ForegroundColor White
}

# ── Windows version ──────────────────────────────────────────────────────────
Write-Step "Checking Windows"
$winVer = [Environment]::OSVersion.Version
if ($winVer.Major -lt 10 -or ($winVer.Major -eq 10 -and $winVer.Build -lt 17763)) {
    Write-Fail "Metis needs Windows 10 version 1809 or later. This is $winVer."
}
Write-OK "Windows $($winVer.Major) build $($winVer.Build)"

# ── Install directory ────────────────────────────────────────────────────────
if (-not $InstallDir) {
    $defaultDir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Metis"
    $InstallDir = $defaultDir
    if ($interactive) {
        Write-Host "`n  Where should your Metis folder be? (Enter for $defaultDir)" -ForegroundColor White
        $answer = Read-Host "  >"
        if ($answer.Trim()) { $InstallDir = $answer.Trim() }
    }
}
$InstallDir = [IO.Path]::GetFullPath($InstallDir)
if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }

$logDir = Join-Path $InstallDir "system\install"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$script:LogFile = Join-Path $logDir "install-log.txt"
"Metis install $(Get-Date -Format s)" | Set-Content -Path $script:LogFile -Encoding UTF8
Write-OK "Metis folder: $InstallDir"

# ── Metis files (only when run on its own, outside MetisSetup.exe) ───────────
if (-not (Test-Path (Join-Path $InstallDir "system\mcp-server\pyproject.toml"))) {
    Write-Step "Downloading Metis"
    $zip = Join-Path $env:TEMP "metis-main.zip"
    $unz = Join-Path $env:TEMP "metis-main"
    Invoke-WebRequest -Uri "https://github.com/SVerITG/Metis/archive/refs/heads/main.zip" `
        -OutFile $zip -UseBasicParsing
    if (Test-Path $unz) { Remove-Item $unz -Recurse -Force }
    Expand-Archive -Path $zip -DestinationPath $unz -Force
    $top = Get-ChildItem $unz | Select-Object -First 1
    Get-ChildItem $top.FullName | Copy-Item -Destination $InstallDir -Recurse -Force
    Remove-Item $zip, $unz -Recurse -Force -ErrorAction SilentlyContinue
    Write-OK "Metis files in place"
}

foreach ($folder in @("journal", "inbox", "inputs\meetings", "inputs\literature",
                      "projects\active", "outputs\reviews", "archive", "system\config")) {
    $dir = Join-Path $InstallDir $folder
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

# ── API key (optional) ───────────────────────────────────────────────────────
if (-not $ApiKey -and $interactive) {
    Write-Host @"

  An Anthropic API key is OPTIONAL. Claude Desktop and Claude Code use your
  Claude subscription. A key (paid, from console.anthropic.com) only powers
  background features such as the automatic morning brief.
  Press Enter to skip; you can add one later.

"@ -ForegroundColor White
    $ApiKey = (Read-Host "  API key (sk-ant-…), or Enter to skip").Trim()
}
$envFile = Join-Path $InstallDir "system\.env"
Set-EnvValue -File $envFile -Key "METIS_RC_ROOT" -Value $InstallDir
Set-EnvValue -File $envFile -Key "ANTHROPIC_API_KEY" -Value $ApiKey

# ── Claude Desktop ───────────────────────────────────────────────────────────
$claude = Find-ClaudeDesktop
if (-not $claude -and -not $SkipClaude) {
    Write-Step "Installing Claude Desktop"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $code = Invoke-Logged "winget" @("install", "--id", "Anthropic.Claude", "--silent",
                                         "--accept-package-agreements", "--accept-source-agreements")
        $claude = Find-ClaudeDesktop
    }
    if ($claude) { Write-OK "Claude Desktop installed" }
    else { Write-Warn "Could not install Claude Desktop automatically. Get it from https://claude.ai/download — Metis connects itself when you do." }
}

# ── uv: provides Python and installs packages ───────────────────────────────
# uv fetches its own Python of the right version, so a computer whose only
# Python is too new (3.14, python.org's default) or absent works the same.
Write-Step "Preparing Python (2–3 minutes the first time)"
$uv = $null
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) { $uv = $uvCmd.Source }
$uvHome = Join-Path $HOME ".local\bin\uv.exe"
if (-not $uv -and (Test-Path $uvHome)) { $uv = $uvHome }
if (-not $uv) {
    try {
        $installer = Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing
        $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $env:UV_NO_MODIFY_PATH = "1"
        Invoke-Expression $installer *>> $script:LogFile
        $ErrorActionPreference = $old
    }
    catch { "uv install failed: $_" | Add-Content -Path $script:LogFile }
    if (Test-Path $uvHome) { $uv = $uvHome }
}

$mcpSrc  = Join-Path $InstallDir "system\mcp-server"
$venv    = Join-Path $mcpSrc ".venv-win"
$venvPy  = Join-Path $venv "Scripts\python.exe"
$lock    = Join-Path $mcpSrc "requirements.txt"
$appReq  = Join-Path $InstallDir "system\app-py\requirements.txt"

if (-not (Test-Path $venvPy)) {
    if ($uv) {
        $code = Invoke-Logged $uv @("venv", "--python", $PythonVersion, $venv)
        if ($code -ne 0) { Write-Fail "Could not create the Python environment." }
    }
    else {
        # No uv (offline or blocked): fall back to a Python on this computer.
        $bootstrap = Join-Path $InstallDir "system\install\bootstrap_python.ps1"
        $code = Invoke-Logged "powershell.exe" @("-NoProfile", "-ExecutionPolicy", "Bypass",
                                                 "-File", $bootstrap, "-InstallDir", $InstallDir)
        $pathFile = Join-Path $InstallDir "system\install\.python-path"
        if ($code -ne 0 -or -not (Test-Path $pathFile)) {
            Write-Fail "No suitable Python (3.11–3.13) could be found or installed."
        }
        $basePy = (Get-Content $pathFile -Encoding UTF8 | Select-Object -First 1).Trim()
        $code = Invoke-Logged $basePy @("-m", "venv", $venv)
        if ($code -ne 0) { Write-Fail "Could not create the Python environment." }
    }
}
Write-OK "Python environment ready"

# Every install runs under the version lock: the versions that were tested.
function Install-Packages {
    param([string[]]$Packages)
    $constraint = @()
    if (Test-Path $lock) { $constraint = @("-c", $lock) }
    if ($uv) {
        return Invoke-Logged $uv (@("pip", "install", "--python", $venvPy) + $constraint + $Packages)
    }
    return Invoke-Logged $venvPy (@("-m", "pip", "install") + $constraint + $Packages)
}

Write-Step "Installing the Metis tools (3–6 minutes)"
if ((Install-Packages @("$mcpSrc[$Extras]")) -ne 0) {
    Write-Warn "An optional part failed — retrying with semantic search only."
    if ((Install-Packages @("$mcpSrc[embedding]")) -ne 0) {
        Write-Warn "Retrying without any optional parts — semantic search will be off."
        if ((Install-Packages @($mcpSrc)) -ne 0) { Write-Fail "The Metis tools could not be installed." }
    }
}
if ((Invoke-Logged $venvPy @("-c", "import metis_mcp.server")) -ne 0) {
    Write-Fail "The Metis tools installed but do not start."
}
Write-OK "Metis tools installed"

if (-not $Stage1Only) {
    Write-Step "Installing the dashboard"
    if ((Install-Packages @("-r", $appReq, "pystray>=0.19", "Pillow>=10.0")) -ne 0) {
        Write-Fail "The dashboard could not be installed."
    }
    Write-OK "Dashboard installed"
}

# ── Database ─────────────────────────────────────────────────────────────────
$env:METIS_RC_ROOT = $InstallDir
$initDb = Join-Path $InstallDir "system\installer\init_db.py"
if ((Invoke-Logged $venvPy @($initDb)) -ne 0) { Write-Fail "The database could not be created." }
Write-OK "Database ready"

# Pre-fetch the search model while online: the server starts offline.
Write-Step "Downloading the search model (about 200 MB, once)"
if ((Invoke-Logged $venvPy @("-c", "from metis_mcp.embeddings import embed_query; embed_query('warmup')")) -eq 0) {
    Write-OK "Search works offline from the first start"
}
else {
    Write-Warn "Could not download it now; it downloads the first time you are online."
}

# ── Connect Claude Desktop ───────────────────────────────────────────────────
Write-Step "Connecting Claude Desktop"
$register = Join-Path $InstallDir "system\install\register_desktop.py"
if ((Invoke-Logged $venvPy @($register, "--python", $venvPy, "--root", $InstallDir)) -eq 0) {
    Write-OK "Metis added to Claude Desktop (your other connectors are kept)"
}
else {
    Write-Warn "Claude Desktop's settings file could not be read, so it was left alone. See the log."
}

# ── Connect Claude Code (if installed) ───────────────────────────────────────
$claudeCli = Get-Command claude -ErrorAction SilentlyContinue
if ($claudeCli) {
    Write-Step "Connecting Claude Code"
    Invoke-Logged $claudeCli.Source @("mcp", "remove", "--scope", "user", "metis-rc") | Out-Null
    $code = Invoke-Logged $claudeCli.Source @("mcp", "add", "--scope", "user",
                                              "-e", "METIS_RC_ROOT=$InstallDir",
                                              "metis-rc", "--", $venvPy, "-m", "metis_mcp.server")
    if ($code -eq 0) { Write-OK "Metis added to Claude Code" }
    else { Write-Warn "Claude Code did not accept the connection; see the log." }
}

# ── Personal Claude instructions: add a Metis section, never replace ─────────
# %USERPROFILE%\.claude\CLAUDE.md is the person's OWN instructions for Claude
# Code. The old installer overwrote it. Now Metis keeps one marked section and
# rewrites only that section on a reinstall.
$claudeDir = Join-Path $env:USERPROFILE ".claude"
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null }
$claudeMd = Join-Path $claudeDir "CLAUDE.md"
$firstRun = Join-Path $InstallDir "system\config\.first-run"
if (-not (Test-Path $firstRun)) { New-Item -ItemType File -Path $firstRun -Force | Out-Null }
$block = @"
<!-- metis:start — written by the Metis installer; edit outside these markers -->
## Metis

You are Metis, a research companion. Metis folder: $InstallDir

If the file ``$firstRun`` exists, start the setup conversation in
$InstallDir\system\config\first-run-wizard.md before anything else, and delete
that file at the end.

Speak plain English, warmly, without jargon. Full routing:
$InstallDir\agents\metis\system-prompt.md
<!-- metis:end -->
"@
$existing = ""
if (Test-Path $claudeMd) { $existing = [IO.File]::ReadAllText($claudeMd) }
$pattern = "(?s)<!-- metis:start.*?<!-- metis:end -->"
if ($existing -match $pattern) {
    $updated = [regex]::Replace($existing, $pattern, { param($m) $block })
}
elseif ($existing.Trim()) {
    $updated = $existing.TrimEnd() + "`r`n`r`n" + $block + "`r`n"
}
else {
    $updated = $block + "`r`n"
}
[IO.File]::WriteAllText($claudeMd, $updated, (New-Object Text.UTF8Encoding($false)))
Write-OK "Metis section added to your Claude instructions (the rest is untouched)"

# ── Shortcuts ────────────────────────────────────────────────────────────────
$icon = Join-Path $InstallDir "system\install\windows\metis-brain.ico"
if ($claude) {
    # Always one in the Metis folder: setup's "Launch Claude" button opens it.
    $aiLinks = @(Join-Path $InstallDir "Metis — Open AI.lnk")
    if ($DesktopShortcut -or -not $FromInstaller) {
        $aiLinks += Join-Path ([Environment]::GetFolderPath("Desktop")) "Metis — Open AI.lnk"
    }
    if ($StartMenuShortcut -or -not $FromInstaller) {
        $aiLinks += Join-Path ([Environment]::GetFolderPath("Programs")) "Metis\Metis — Open AI.lnk"
    }
    foreach ($l in $aiLinks) {
        New-Shortcut -Path $l -Target $claude.Target -Arguments $claude.Arguments `
            -Icon $icon -Description "Open Claude Desktop with Metis"
    }
}
# Dashboard shortcuts belong to MetisSetup.exe when it runs this script; only a
# standalone run makes its own.
if (-not $Stage1Only -and -not $FromInstaller) {
    $vbs = Join-Path $InstallDir "system\install\windows\launch-dashboard-silent.vbs"
    foreach ($l in @((Join-Path ([Environment]::GetFolderPath("Desktop")) "Metis.lnk"),
                     (Join-Path ([Environment]::GetFolderPath("Programs")) "Metis\Metis — Dashboard.lnk"))) {
        New-Shortcut -Path $l -Target "$env:WINDIR\System32\wscript.exe" -Arguments "`"$vbs`"" `
            -Icon $icon -Description "Open the Metis dashboard"
    }
}
Write-OK "Shortcuts created"

# ── Done ─────────────────────────────────────────────────────────────────────
"Completed $(Get-Date -Format s)" | Add-Content -Path $script:LogFile
Write-Host "`n  Metis is installed." -ForegroundColor Green
if ($interactive) {
    Write-Host @"

  Open Claude Desktop ("Metis — Open AI") and say hello: Metis will introduce
  itself and ask a few questions to set itself up for your work.
$(if (-not $Stage1Only) { "  The dashboard opens from the ""Metis"" shortcut on your desktop.`n" })
  Your Metis folder: $InstallDir

"@ -ForegroundColor White
    if ($claude) {
        $go = Read-Host "  Open Claude Desktop now? (Y/n)"
        if ($go -notmatch "^[nN]") {
            if ($claude.Arguments) { Start-Process -FilePath $claude.Target -ArgumentList $claude.Arguments }
            else { Start-Process -FilePath $claude.Target }
        }
    }
}
exit 0
