# build-windows-installers.ps1
# Compiles the 3 Metis Windows exe installers locally and uploads them to GitHub.
#
# Usage (from PowerShell on Windows):
#   cd "C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\Research Cortex\metis\system\install"
#   .\build-windows-installers.ps1
#
# Optional: skip upload if you just want the exe files:
#   .\build-windows-installers.ps1 -SkipUpload

param(
    [string]$Version = "1.0",
    [switch]$SkipUpload
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$IssFile   = Join-Path $ScriptDir "installer\metis-setup.iss"
$DistDir   = Join-Path $ScriptDir "installer\dist"

# ── 1. Find ISCC ────────────────────────────────────────────────────────────
$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue)?.Source
if (-not $iscc) { $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) {
    Write-Error "Inno Setup not found. Download from https://jrsoftware.org/isdl.php and install, then re-run."
    exit 1
}
Write-Host "Using ISCC: $iscc" -ForegroundColor Cyan

# ── 2. Compile three variants ─────────────────────────────────────────────
$types = @("full", "standard", "minimal")
foreach ($type in $types) {
    Write-Host "`nCompiling $type installer..." -ForegroundColor Yellow
    & $iscc /DDefaultType=$type /DMyAppVersion=$Version $IssFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ISCC failed for type=$type (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

# ── 3. List output files ──────────────────────────────────────────────────
Write-Host "`nBuilt installers:" -ForegroundColor Green
Get-ChildItem "$DistDir\*.exe" | ForEach-Object {
    Write-Host ("  {0}  ({1} MB)" -f $_.Name, [math]::Round($_.Length/1MB, 1))
}

if ($SkipUpload) {
    Write-Host "`nDone. Skipped GitHub upload (-SkipUpload)." -ForegroundColor Green
    exit 0
}

# ── 4. Upload to GitHub Release ───────────────────────────────────────────
$gh = (Get-Command gh -ErrorAction SilentlyContinue)?.Source
if (-not $gh) {
    Write-Host "`ngh CLI not found — upload manually from: $DistDir" -ForegroundColor Yellow
    exit 0
}

$tag = "v$Version"
$exes = Get-ChildItem "$DistDir\MetisSetup-*-$Version.exe" | Select-Object -ExpandProperty FullName

# Create release if it doesn't exist; upload assets either way
$releaseExists = gh release view $tag --repo SVerITG/Metis 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nCreating GitHub Release $tag..." -ForegroundColor Yellow
    gh release create $tag @exes `
        --repo SVerITG/Metis `
        --title "Metis $Version" `
        --notes "Metis Research Cortex $Version — base release.

### Windows Installers
| File | Includes | Best for |
|---|---|---|
| MetisSetup-full-$Version.exe | Core + dashboard + Statistics course | New users |
| MetisSetup-standard-$Version.exe | Core + dashboard | Dashboard without course |
| MetisSetup-minimal-$Version.exe | Core (MCP + agents) only | Developers |

Requires: Windows 10+, Python 3.10+, Anthropic API key, Claude Desktop."
} else {
    Write-Host "`nRelease $tag exists — uploading assets..." -ForegroundColor Yellow
    foreach ($exe in $exes) {
        gh release upload $tag $exe --repo SVerITG/Metis --clobber
    }
}

Write-Host "`nDone. Release: https://github.com/SVerITG/Metis/releases/tag/$tag" -ForegroundColor Green
