<#
  build-bundled-exe.ps1 - build the bundled end-user metis.exe (PyInstaller).

  MUST run on Windows with a real Windows Python 3.10-3.13 on the machine (NOT WSL - a
  WSL build produces a Linux binary; NOT 3.14+ - several native deps have no 3.14 wheels
  yet). The script auto-selects a compatible interpreter via the 'py' launcher. It creates
  an isolated build venv, installs the project dependencies + PyInstaller, and freezes the
  launcher per metis.spec.

  Usage (from a PowerShell prompt):
      cd "<RepoRoot>\system\install\installer\pyinstaller"
      .\build-bundled-exe.ps1

  Output: dist\metis\  (metis.exe + _internal\). Smoke-tested at the end with
  `metis.exe --version` and `metis.exe doctor`.

  NOTE: this file is intentionally pure ASCII - non-ASCII chars (em-dashes, checkmarks)
  break PowerShell parsing when the file is read as ANSI.
#>
$ErrorActionPreference = "Stop"

# -- Resolve repo root from this script's location -----------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path   # ...\installer\pyinstaller
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir "..\..\..\..")).Path
$Spec      = Join-Path $ScriptDir "metis.spec"
$BuildDir  = Join-Path $ScriptDir "build"
$DistDir   = Join-Path $ScriptDir "dist"
$VenvDir   = Join-Path $ScriptDir ".venv-build"

Write-Host "Repo root : $RepoRoot"
Write-Host "Spec      : $Spec"

# -- Locate a compatible Windows Python (3.10-3.13) ----------------------------
# Prefer the 'py' launcher with an explicit version; fall back to bare 'python' only
# if its version is in range. 3.14+ is rejected with a clear message.
function Test-PyVersion($exe) {
    try {
        $v = & $exe -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null
        return $v.Trim()
    } catch { return $null }
}

$PyExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($ver in @("3.13", "3.12", "3.11", "3.10")) {
        & py "-$ver" -c "print(1)" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            # resolve the actual exe path for this version
            $PyExe = (& py "-$ver" -c "import sys;print(sys.executable)").Trim()
            Write-Host "Python    : $PyExe (via py -$ver)"
            break
        }
    }
}
if (-not $PyExe) {
    $bare = (Get-Command python -ErrorAction SilentlyContinue)
    if ($bare) {
        $bv = Test-PyVersion $bare.Source
        if ($bv -and [version]$bv -ge [version]"3.10" -and [version]$bv -lt [version]"3.14") {
            $PyExe = $bare.Source
            Write-Host "Python    : $PyExe ($bv)"
        }
    }
}
if (-not $PyExe) {
    Write-Host ""
    Write-Host "ERROR: no compatible Python found." -ForegroundColor Red
    Write-Host "Metis deps need Python 3.10-3.13 (you have 3.14, which has no wheels yet for"
    Write-Host "onnxruntime / pyreadstat / pymupdf). Install 3.13 from:"
    Write-Host "    https://www.python.org/downloads/release/python-3137/"
    Write-Host "Tick 'py launcher' during install, then re-run this script - it will pick 3.13"
    Write-Host "automatically while leaving your 3.14 as the default 'python'."
    exit 1
}

# -- Fresh build venv ----------------------------------------------------------
if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
& $PyExe -m venv $VenvDir
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"

& $VenvPy -m pip install --upgrade pip wheel | Out-Host

# Install the MCP server (pulls all runtime deps via its pyproject) + the dashboard's
# own requirements + PyInstaller.
$McpProj = Join-Path $RepoRoot "system\mcp-server"
$AppReq  = Join-Path $RepoRoot "system\app-py\requirements.txt"

Write-Host "Installing dependencies (this can take several minutes)..."
& $VenvPy -m pip install "$McpProj" | Out-Host
if (Test-Path $AppReq) { & $VenvPy -m pip install -r $AppReq | Out-Host }
& $VenvPy -m pip install "pyinstaller>=6.0" | Out-Host

# -- Freeze --------------------------------------------------------------------
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
if (Test-Path $DistDir)  { Remove-Item -Recurse -Force $DistDir }

Write-Host "Running PyInstaller..."
& $VenvPy -m PyInstaller --noconfirm --clean `
    --distpath $DistDir --workpath $BuildDir `
    $Spec | Out-Host

$ExePath = Join-Path $DistDir "metis\metis.exe"
if (-not (Test-Path $ExePath)) { throw "Build failed - metis.exe not found at $ExePath" }

# -- Smoke test ----------------------------------------------------------------
Write-Host ""
Write-Host "-- Smoke test --------------------------------"
& $ExePath --version | Out-Host
& $ExePath doctor     | Out-Host

Write-Host ""
Write-Host "OK Built: $ExePath"
Write-Host "  Next: package dist\metis\ into the Inno installer (DefaultType=bundled),"
Write-Host "  or run it directly:  metis.exe dashboard   /   metis.exe mcp"
