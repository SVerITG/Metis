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
.PARAMETER WizardAnswers
    The answers MetisSetup.exe collected (name, role, interests, projects). They
    are applied here, before the first self-check, so that check sees a profile.
.PARAMETER LoadDemo
    Load the example workspace (only into a workspace that is still empty).
.PARAMETER MorningBriefing
    HH:MM to have Claude Desktop write the morning briefing every weekday at
    that time (a Desktop scheduled task), or "off". Empty, as on an update:
    keep what was chosen before.

.NOTES
    Exit code 0 = installed (possibly with warnings), 1 = not installed. The
    setup program reads it: a failed install must never end on "finished".
#>
param(
    [switch]$Stage1Only,
    [switch]$FromInstaller,
    [switch]$DesktopShortcut,
    [switch]$StartMenuShortcut,
    [switch]$SkipClaude,
    [switch]$SkipPython,
    [switch]$LoadDemo,
    [string]$InstallDir    = "",
    [string]$ApiKey        = "",
    [string]$WizardAnswers = "",
    [string]$MorningBriefing = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$interactive = -not $FromInstaller -and [Environment]::UserInteractive

# Older Windows 10 builds offer only TLS 1.0/1.1 to PowerShell 5.1 by default,
# and every download host here requires 1.2: "Could not create SSL/TLS secure channel".
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

# Everything machine-specific lives OUTSIDE the Metis folder, in
# %LOCALAPPDATA%\Metis. The Metis folder defaults to Documents, and on an
# institutional laptop Documents is usually inside OneDrive: a Python
# environment there means thousands of files syncing, files-on-demand turning
# a library into a placeholder that cannot be loaded, and paths deep enough to
# pass Windows' 260-character limit. Local app data is never synced.
$MetisLocal = Join-Path $env:LOCALAPPDATA "Metis"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $MetisLocal "python"   # default is the ROAMING profile
$env:UV_CACHE_DIR          = Join-Path $MetisLocal "uv-cache"
# Use the Windows certificate store, so a network that re-signs HTTPS with an
# institutional certificate does not break every download.
$env:UV_NATIVE_TLS = "1"

# On Windows on ARM, use the x64 build of Python: it runs under Windows'
# built-in emulation, and every package Metis needs is published for x64,
# which is not true of ARM64.
$isArm = ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") -or ("$env:PROCESSOR_ARCHITEW6432" -eq "ARM64")

# The extras every installer adds by default.
# voice is left out: it compiles C, and a laptop without a compiler failed.
# office is in: without python-docx and python-pptx every template action
# (slides, posters, letters filled into the researcher's own templates)
# answers with an install line instead of a file.
$Extras = "embedding,library,ocr,office"
$PythonVersion = "3.12"   # pyproject.toml: >=3.10,<3.14
if ($isArm) { $PythonVersion = "cpython-3.12-windows-x86_64-none" }

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

# Stop every running copy of Metis: the server Claude Desktop started, the
# dashboard, a self-check. Windows will not replace a file a running program has
# loaded, so updating while Claude Desktop is open failed half-way through. A
# venv's python.exe only relays to the real interpreter, so the interpreter is
# recognised by its folder (our own Python) or by what it is running.
function Stop-Metis {
    param([string[]]$Roots)
    try {
        Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
            Where-Object {
                $exe = "$($_.ExecutablePath)"; $cmd = "$($_.CommandLine)"
                ($cmd -match "metis_mcp|uvicorn main:app|metis_verify") -or
                (@($Roots | Where-Object { $_ -and $exe.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) }).Count -gt 0)
            } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
    }
    catch { "stopping Metis: $_" | Add-Content -Path $script:LogFile }
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

# ── Network ──────────────────────────────────────────────────────────────────
# A browser finds an institutional proxy through Windows' settings; Python's
# tools only read HTTPS_PROXY. Hand them the same proxy, here and (through
# system\.env) to Metis itself later.
if (-not $env:HTTPS_PROXY) {
    try {
        $sysProxy = [Net.WebRequest]::GetSystemWebProxy()
        $sysProxy.Credentials = [Net.CredentialCache]::DefaultCredentials
        $probe = [Uri]"https://pypi.org/simple/"
        $via = $sysProxy.GetProxy($probe)
        if ($via -and $via.Host -ne $probe.Host) {
            $env:HTTPS_PROXY = $via.AbsoluteUri.TrimEnd("/")
            $env:HTTP_PROXY  = $env:HTTPS_PROXY
            Set-EnvValue -File $envFile -Key "HTTPS_PROXY" -Value $env:HTTPS_PROXY
            Set-EnvValue -File $envFile -Key "HTTP_PROXY"  -Value $env:HTTPS_PROXY
            "proxy: $env:HTTPS_PROXY" | Add-Content -Path $script:LogFile
        }
    }
    catch { "proxy detection: $_" | Add-Content -Path $script:LogFile }
}
if ([Net.WebRequest]::DefaultWebProxy) {
    [Net.WebRequest]::DefaultWebProxy.Credentials = [Net.CredentialCache]::DefaultCredentials
}

# Setup downloads about 1 GB the first time. Without a connection it cannot
# work, and saying so now beats failing ten minutes in with a package error.
$online = $true
try { Invoke-WebRequest -Uri "https://pypi.org/simple/pip/" -Method Head -UseBasicParsing -TimeoutSec 20 | Out-Null }
catch { $online = $false; "connectivity: $_" | Add-Content -Path $script:LogFile }

# ── Claude Desktop ───────────────────────────────────────────────────────────
# METIS_SKIP_CLAUDE lets the release build's install test skip the download.
if ($env:METIS_SKIP_CLAUDE -eq "1") { $SkipClaude = $true }
$claude = Find-ClaudeDesktop
if (-not $claude -and -not $SkipClaude) {
    Write-Step "Installing Claude Desktop"
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        # Time-limited: winget can wait on a prompt nobody sees, and setup must
        # never hang on an optional step.
        $wp = Start-Process -FilePath $winget.Source -WindowStyle Hidden -PassThru -ArgumentList `
            "install", "--id", "Anthropic.Claude", "--silent", "--scope", "user",
            "--accept-package-agreements", "--accept-source-agreements"
        if (-not $wp.WaitForExit(600000)) {
            Stop-Process -Id $wp.Id -Force -ErrorAction SilentlyContinue
            "winget: timed out after 10 minutes" | Add-Content -Path $script:LogFile
        }
        $claude = Find-ClaudeDesktop
    }
    if ($claude) { Write-OK "Claude Desktop installed" }
    else { Write-Warn "Could not install Claude Desktop automatically. Get it from https://claude.ai/download — Metis connects itself when you do." }
}

# ── uv: provides Python and installs packages ───────────────────────────────
# uv fetches its own Python of the right version, so a computer whose only
# Python is too new (3.14, python.org's default) or absent works the same.
Write-Step "Preparing Python (2–3 minutes the first time)"
$mcpSrc  = Join-Path $InstallDir "system\mcp-server"
$venv    = Join-Path $MetisLocal "venv"
$venvPy  = Join-Path $venv "Scripts\python.exe"
$oldVenv = Join-Path $mcpSrc ".venv-win"     # where versions up to 1.2 put it
$lock    = Join-Path $mcpSrc "requirements.txt"
$appReq  = Join-Path $InstallDir "system\app-py\requirements.txt"

if (-not $online) {
    if (Test-Path $venvPy) {
        Write-Warn "No internet connection: keeping the Metis tools as they are."
    }
    else {
        Write-Fail ("Setup needs an internet connection (it downloads about 1 GB the first time), " +
                    "and pypi.org could not be reached. Connect to the internet - or ask IT whether " +
                    "pypi.org, files.pythonhosted.org and github.com are blocked - and run setup again.")
    }
}

# A copy of Metis that is running (Claude Desktop starts one) holds its files open.
Stop-Metis @($venv, $oldVenv, $env:UV_PYTHON_INSTALL_DIR)

# uv: one small program, downloaded directly. The official one-line installer
# is the fallback only, because it is a downloaded script that is RUN, which
# managed computers often forbid.
$uv = $null
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) { $uv = $uvCmd.Source }
$uvLocal = Join-Path $MetisLocal "bin\uv.exe"
foreach ($candidate in @($uvLocal, (Join-Path $HOME ".local\bin\uv.exe"))) {
    if (-not $uv -and (Test-Path $candidate)) { $uv = $candidate }
}
if (-not $uv -and $online) {
    $arch = if ($isArm) { "aarch64" } else { "x86_64" }
    $zip = Join-Path $env:TEMP "metis-uv.zip"
    $unz = Join-Path $env:TEMP "metis-uv"
    try {
        Invoke-WebRequest -UseBasicParsing -OutFile $zip `
            -Uri "https://github.com/astral-sh/uv/releases/latest/download/uv-$arch-pc-windows-msvc.zip"
        if (Test-Path $unz) { Remove-Item $unz -Recurse -Force }
        Expand-Archive -Path $zip -DestinationPath $unz -Force
        $found = Get-ChildItem $unz -Recurse -Filter uv.exe | Select-Object -First 1
        if ($found) {
            New-Item -ItemType Directory -Path (Split-Path $uvLocal) -Force | Out-Null
            Copy-Item $found.FullName $uvLocal -Force
            $uv = $uvLocal
        }
    }
    catch { "uv download failed: $_" | Add-Content -Path $script:LogFile }
    Remove-Item $zip, $unz -Recurse -Force -ErrorAction SilentlyContinue
}
if (-not $uv -and $online) {
    try {
        $installer = Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing
        $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $env:UV_NO_MODIFY_PATH = "1"
        Invoke-Expression $installer *>> $script:LogFile
        $ErrorActionPreference = $old
    }
    catch { "uv install script failed: $_" | Add-Content -Path $script:LogFile }
    $uvHome = Join-Path $HOME ".local\bin\uv.exe"
    if (Test-Path $uvHome) { $uv = $uvHome }
}

if (-not (Test-Path $venvPy)) {
    if ($uv) {
        # only-managed: uv's own Python, never whatever else is on the computer
        # (an Anaconda base, the Microsoft Store stub, a half-removed old copy).
        $code = Invoke-Logged $uv @("venv", "--python", $PythonVersion,
                                    "--python-preference", "only-managed", $venv)
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
    Write-Warn "An optional part failed — retrying with semantic search and documents only."
    if ((Install-Packages @("$mcpSrc[embedding,office]")) -ne 0) {
        Write-Warn "Retrying without any optional parts — semantic search will be off."
        if ((Install-Packages @($mcpSrc)) -ne 0) { Write-Fail "The Metis tools could not be installed." }
    }
}
# The search engine (onnxruntime) needs Microsoft's Visual C++ runtime, which
# most computers have because Office or Teams brought it, but a freshly imaged
# one may not. Test the import itself; install the runtime only when it fails.
$ortTest = @("-c", "import onnxruntime")
if ((Invoke-Logged $venvPy $ortTest) -ne 0) {
    Write-Step "Installing Microsoft's Visual C++ runtime (Windows may ask your permission)"
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    $redist = if ($isArm) { "Microsoft.VCRedist.2015+.arm64" } else { "Microsoft.VCRedist.2015+.x64" }
    if ($winget) {
        $wp = Start-Process -FilePath $winget.Source -WindowStyle Hidden -PassThru -ArgumentList `
            "install", "--id", $redist, "--silent", "--accept-package-agreements", "--accept-source-agreements"
        if (-not $wp.WaitForExit(600000)) { Stop-Process -Id $wp.Id -Force -ErrorAction SilentlyContinue }
    }
    if ((Invoke-Logged $venvPy $ortTest) -eq 0) { Write-OK "Visual C++ runtime installed" }
    else {
        Write-Warn ("Search inside your documents needs the 'Microsoft Visual C++ Redistributable', " +
                    "which could not be installed without administrator rights. Ask IT to install it " +
                    "(https://aka.ms/vs/17/release/vc_redist.x64.exe); everything else works meanwhile.")
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

# ── Your answers from setup, and the example workspace ───────────────────────
# Applied BEFORE the first self-check, which would otherwise report a fresh
# colleague as having no profile right after they typed it in.
if ($WizardAnswers -and (Test-Path $WizardAnswers)) {
    Write-Step "Personalising Metis with your answers"
    $wizard = Join-Path $InstallDir "system\install\process_wizard_answers.py"
    if ((Invoke-Logged $venvPy @($wizard, "--answers", $WizardAnswers, "--metis-root", $InstallDir, "--quiet")) -eq 0) {
        Write-OK "Your profile is saved"
    }
    else { Write-Warn "Your answers could not be saved; Metis will ask for them in your first conversation." }
}
if ($LoadDemo) {
    $demo = Join-Path $InstallDir "system\install\seed_mockup_demo.py"
    if (Test-Path $demo) {
        if ((Invoke-Logged $venvPy @($demo, "--load", "--quiet")) -eq 0) { Write-OK "Example workspace loaded" }
        else { Write-Warn "The example workspace was not loaded (it is only added to an empty workspace)." }
    }
}
$kb = Join-Path $InstallDir "system\install\build_knowledge_db.py"
if (-not $Stage1Only -and (Test-Path $kb)) {
    Write-Step "Reading the documents that come with Metis (a few minutes)"
    if ((Invoke-Logged $venvPy @($kb, "--library-dir", (Join-Path $InstallDir "knowledge\library"), "--quiet")) -eq 0) {
        Write-OK "Included documents are searchable"
    }
    else { Write-Warn "The included documents were not indexed; Metis indexes them later." }
}

# ── Connect Claude Desktop ───────────────────────────────────────────────────
Write-Step "Connecting Claude Desktop"
$register = Join-Path $InstallDir "system\install\register_desktop.py"
# Claude Desktop always (it is installed above when missing), and VS Code and
# Cursor when they are on this computer.
if ((Invoke-Logged $venvPy @($register, "--all-installed", "--python", $venvPy, "--root", $InstallDir)) -eq 0) {
    Write-OK "Metis added to Claude Desktop and your other AI apps (your other connectors are kept)"
}
else {
    Write-Warn "Claude Desktop's settings file could not be read, so it was left alone. See the log."
}

# ── The morning briefing: a Claude Desktop scheduled task ───────────────────
# The standard way the briefing is written, on the person's own subscription.
# Without a signed-in Claude Desktop the task cannot be registered yet; the
# daily self-check finishes it ("morning_briefing" in essentials.json).
$schedule = Join-Path $InstallDir "system\install\register_schedule.py"
if ($MorningBriefing -eq "off") {
    Invoke-Logged $venvPy @($schedule, "--remove") | Out-Null
}
elseif ($MorningBriefing -or (Test-Path (Join-Path $env:USERPROFILE ".claude\scheduled-tasks\metis-morning-briefing"))) {
    Write-Step "Setting up the morning briefing in Claude Desktop"
    $schedArgs = @($schedule, "--root", $InstallDir)
    if ($MorningBriefing) { $schedArgs += @("--time", $MorningBriefing) }
    if ((Invoke-Logged $venvPy $schedArgs) -eq 0) {
        Write-OK "Claude Desktop will write your briefing every weekday (Claude Desktop -> Scheduled)"
    }
    else { Write-Warn "The morning briefing could not be scheduled; the self-check will try again." }
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

# ── Background tasks: the daily self-check, and the dashboard at log-on ─────
# Defined in one place, register-tasks.ps1, which the install doctor also uses
# to repair a missing task. The self-check is the install doctor itself: it
# checks everything Metis needs and repairs what it can; the dashboard shows
# its verdict. The dashboard does the background work — the morning news and
# literature scans, reminders, backups — but only while it runs.
Write-Step "Scheduling the daily self-check and the dashboard"
$verify = Join-Path $InstallDir "system\install\metis_verify.py"
$taskArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
              (Join-Path $InstallDir "system\install\windows\register-tasks.ps1"), "-InstallDir", $InstallDir)
if ($Stage1Only) { $taskArgs += "-Stage1Only" }
if ((Invoke-Logged "powershell.exe" $taskArgs) -eq 0) {
    Write-OK "Metis checks itself every day (and repairs what it can)"
    if (-not $Stage1Only) { Write-OK "The dashboard starts by itself when you log on" }
}
else {
    Write-Warn "Not every background task could be scheduled; the self-check will report what is missing."
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

# ── First self-check, so the dashboard has a verdict from the start ──────────
Write-Step "Checking that everything works"
if ((Invoke-Logged $venvPy @($verify, "--fix")) -le 1) {
    Write-OK "Metis works with Claude on this computer"
}
else {
    Write-Warn "Something still needs attention — see the Metis tab on the dashboard, or ask Metis to check."
}

# ── Tidy up an older install, start the dashboard ───────────────────────────
# Versions up to 1.2 kept the Python environment inside the Metis folder. Now
# that Claude Desktop and Claude Code point at the new one, the old copy is
# only a gigabyte of files for OneDrive to sync.
if ((Test-Path $oldVenv) -and (Test-Path $venvPy)) {
    Remove-Item $oldVenv -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $oldVenv)) { Write-OK "Removed the previous version's Python copy from your Metis folder" }
}
if (-not $Stage1Only -and $env:METIS_SKIP_DASHBOARD_START -ne "1") {
    $vbsBg = Join-Path $InstallDir "system\install\windows\launch-dashboard-silent.vbs"
    if (Test-Path $vbsBg) { Start-Process "$env:WINDIR\System32\wscript.exe" -ArgumentList "`"$vbsBg`"", "/background" }
}

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
