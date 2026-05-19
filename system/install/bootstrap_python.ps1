<#
.SYNOPSIS
    bootstrap_python.ps1 — Embedded Python bootstrap for Metis (M11.4)

.DESCRIPTION
    Ensures a working Python 3.11+ interpreter is available for the Metis venv.
    Strategy (in order):
      1. Use existing Python 3.11+ on PATH or in well-known locations
      2. Install via winget (silent, no window)
      3. Download python.org full installer (internet required)
      4. Extract bundled embeddable Python from {InstallDir}\vendor\python-embed.zip
         (The embeddable zip is bundled by the Inno Setup installer from vendor/)

    Returns the path to a working python.exe via $env:METIS_PYTHON.
    Exits with code 1 if no Python can be obtained.

.PARAMETER InstallDir
    Root of the Metis installation (contains vendor\ folder if using offline bundle).

.PARAMETER OfflineOnly
    Skip internet download attempts. Requires bundled embed zip in vendor\.

.EXAMPLE
    .\bootstrap_python.ps1 -InstallDir "C:\Users\YourName\Documents\Metis"
#>

[CmdletBinding()]
param(
    [string]$InstallDir = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [switch]$OfflineOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────
function Write-Step  { Write-Host "  → $args" -ForegroundColor Cyan }
function Write-OK    { Write-Host "  ✓ $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "  ⚠ $args" -ForegroundColor Yellow }
function Write-Fail  { Write-Host "  ✗ $args" -ForegroundColor Red; exit 1 }

# ── Step 1: Check existing Python ────────────────────────────────────────────
Write-Step "Checking for existing Python 3.11+"

$pythonExe = $null

# Check PATH first
foreach ($cmd in @("python3.11", "python3", "python")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        $ver = & $found.Source --version 2>&1
        if ($ver -match "3\.1[1-9]|3\.[2-9]\d") {
            $pythonExe = $found.Source
            Write-OK "Found on PATH: $pythonExe ($ver)"
            break
        }
    }
}

# Check well-known Windows install locations if PATH search failed
if (-not $pythonExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $ver = & $c --version 2>&1
            if ($ver -match "3\.1[1-9]") {
                $pythonExe = $c
                Write-OK "Found at known location: $c ($ver)"
                break
            }
        }
    }
}

if ($pythonExe) {
    $env:METIS_PYTHON = $pythonExe
    exit 0
}

# ── Step 2: winget install ───────────────────────────────────────────────────
if (-not $OfflineOnly) {
    Write-Step "Trying winget install (Python 3.11)…"
    $hasWinget = Get-Command winget -ErrorAction SilentlyContinue
    if ($hasWinget) {
        winget install --id Python.Python.3.11 --silent `
            --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path","User")
        $found = Get-Command python -ErrorAction SilentlyContinue
        if ($found) {
            $ver = & $found.Source --version 2>&1
            if ($ver -match "3\.1[1-9]") {
                $pythonExe = $found.Source
                Write-OK "Installed via winget: $pythonExe ($ver)"
                $env:METIS_PYTHON = $pythonExe
                exit 0
            }
        }
        Write-Warn "winget install returned success but python not found on PATH"
    } else {
        Write-Warn "winget not available on this machine"
    }
}

# ── Step 3: Download python.org full installer ───────────────────────────────
if (-not $OfflineOnly) {
    Write-Step "Downloading Python 3.11.9 installer from python.org…"
    $pyVersion  = "3.11.9"
    $pyUrl      = "https://www.python.org/ftp/python/$pyVersion/python-$pyVersion-amd64.exe"
    $pyInstPath = Join-Path $env:TEMP "python-$pyVersion-amd64.exe"
    try {
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstPath -UseBasicParsing -TimeoutSec 120
        Write-Step "Running installer silently…"
        Start-Process -FilePath $pyInstPath `
            -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" `
            -Wait -NoNewWindow
        Remove-Item $pyInstPath -Force -ErrorAction SilentlyContinue
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path","User")
        $found = Get-Command python -ErrorAction SilentlyContinue
        if ($found) {
            $ver = & $found.Source --version 2>&1
            if ($ver -match "3\.1[1-9]") {
                $pythonExe = $found.Source
                Write-OK "Installed from python.org: $pythonExe ($ver)"
                $env:METIS_PYTHON = $pythonExe
                exit 0
            }
        }
    }
    catch {
        Write-Warn "python.org download failed: $_"
    }
}

# ── Step 4: Extract bundled embeddable Python ────────────────────────────────
Write-Step "Using bundled embeddable Python…"

$vendorDir  = Join-Path $InstallDir "vendor"
$embedZip   = Join-Path $vendorDir "python-embed.zip"
$embedDir   = Join-Path $InstallDir "system\python-embed"

if (-not (Test-Path $embedZip)) {
    Write-Fail "No Python found and no bundled embed zip at $embedZip. Cannot continue."
}

# Extract embeddable Python
Write-Step "Extracting $embedZip → $embedDir"
if (Test-Path $embedDir) { Remove-Item $embedDir -Recurse -Force }
Add-Type -Assembly System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($embedZip, $embedDir)

$embedPython = Join-Path $embedDir "python.exe"
if (-not (Test-Path $embedPython)) {
    Write-Fail "Embed extraction failed — python.exe not found in $embedDir"
}

# Enable pip in embeddable Python (edit pythonXX._pth to uncomment import site)
$pthFiles = Get-ChildItem $embedDir -Filter "python*._pth" | Select-Object -First 1
if ($pthFiles) {
    $pthContent = Get-Content $pthFiles.FullName
    $pthContent = $pthContent -replace "^#import site", "import site"
    $pthContent | Set-Content $pthFiles.FullName
}

# Install pip into embeddable Python
Write-Step "Bootstrapping pip into embedded Python…"
$getPipUrl  = "https://bootstrap.pypa.io/get-pip.py"
$getPipPath = Join-Path $env:TEMP "get-pip.py"
if (-not $OfflineOnly) {
    Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath -UseBasicParsing -TimeoutSec 60
    & $embedPython $getPipPath --no-warn-script-location 2>&1 | Out-Null
} else {
    # Offline: pip must already be in the embed zip (bundled via vendor_download.py --vendor-pip)
    $bundledPip = Join-Path $vendorDir "get-pip.py"
    if (Test-Path $bundledPip) {
        & $embedPython $bundledPip --no-index --find-links (Join-Path $vendorDir "pip-wheels") 2>&1 | Out-Null
    } else {
        Write-Fail "Offline mode: get-pip.py not found in $vendorDir"
    }
}

# Verify pip
$pipExe = Join-Path $embedDir "Scripts\pip.exe"
if (-not (Test-Path $pipExe)) {
    Write-Fail "pip installation into embedded Python failed"
}

Write-OK "Embedded Python ready: $embedPython"
$env:METIS_PYTHON    = $embedPython
$env:METIS_PYTHON_DIR = $embedDir
exit 0
