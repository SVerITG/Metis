# build-windows-installers.ps1
# Compiles the Metis Windows installer locally and (optionally) uploads it to GitHub.
#
# The installer is a SINGLE type-selectable exe — full / minimal / custom are
# chosen inside the wizard, not built as separate files (see metis-setup.iss:
# "Single output file — choices are made inside the wizard, not via separate builds").
#
# Usage (from PowerShell on Windows):
#   cd "%METIS_RC_ROOT%\system\install"
#   .\build-windows-installers.ps1
#
# Optional — skip GitHub upload, just build the exe:
#   .\build-windows-installers.ps1 -SkipUpload

param(
    [string]$Version = "1.0",
    [switch]$SkipUpload
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$IssFile   = Join-Path $ScriptDir "installer\metis-setup.iss"
$DistDir   = Join-Path $ScriptDir "installer\dist"

# ── 1. Find ISCC ─────────────────────────────────────────────────────────────
$isccCmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($isccCmd) {
    $iscc = $isccCmd.Source
} else {
    $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
}
if (-not (Test-Path $iscc)) {
    Write-Error "Inno Setup not found at '$iscc'. Download from https://jrsoftware.org/isdl.php and install, then re-run."
    exit 1
}
Write-Host "Using ISCC: $iscc" -ForegroundColor Cyan

# ── 2. Compile the installer ──────────────────────────────────────────────────
# Build into a LOCAL temp dir, not straight into dist/. The repo often lives on
# OneDrive, and SetupIconFile makes ISCC do an in-place EndUpdateResource on the
# output .exe — OneDrive locks the file mid-write and the compile fails (error 32).
# Building locally then copying sidesteps that entirely.
$BuildDir = Join-Path $env:TEMP "metis-build"
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
Write-Host ""
Write-Host "Compiling installer (version $Version)..." -ForegroundColor Yellow
& $iscc "/O$BuildDir" /DMyAppVersion=$Version $IssFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "ISCC failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

# ── 3. Copy the result into dist/ ──────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
$built = Join-Path $BuildDir "MetisSetup-$Version.exe"
$exe   = Join-Path $DistDir  "MetisSetup-$Version.exe"
Copy-Item $built $exe -Force
Remove-Item $BuildDir -Recurse -Force -ErrorAction SilentlyContinue
if (-not (Test-Path $exe)) {
    Write-Error "Expected output not found: $exe"
    exit 1
}
$mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host ""
Write-Host "Built installer:" -ForegroundColor Green
Write-Host "  MetisSetup-$Version.exe  ($mb MB)"

if ($SkipUpload) {
    Write-Host ""
    Write-Host "Done. Skipped GitHub upload (-SkipUpload)." -ForegroundColor Green
    exit 0
}

# ── 4. Upload to GitHub Release (public repo = Metis_PH) ──────────────────────
$Repo = "SVerITG/Metis_PH"   # the public repo the README's download link points at
$ghCmd = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghCmd) {
    Write-Host ""
    Write-Host "gh CLI not found — install it (winget install GitHub.cli; gh auth login)" -ForegroundColor Yellow
    Write-Host "or upload $exe to $Repo release $tag manually on github.com." -ForegroundColor Yellow
    exit 0
}

$tag = "v$Version"

# Release notes (temp file avoids here-string indentation issues)
$notesFile = Join-Path $env:TEMP "metis-release-notes.txt"
"## Metis $Version — install"                                             | Out-File $notesFile -Encoding utf8
""                                                                        | Out-File $notesFile -Append -Encoding utf8
"**Windows:** download **MetisSetup-$Version.exe** below and double-click it."  | Out-File $notesFile -Append -Encoding utf8
"One installer — choose Full (AI + dashboard), Minimal (AI only), or Custom in the wizard." | Out-File $notesFile -Append -Encoding utf8
""                                                                        | Out-File $notesFile -Append -Encoding utf8
"**macOS / Linux:** see the README one-line install."                     | Out-File $notesFile -Append -Encoding utf8
""                                                                        | Out-File $notesFile -Append -Encoding utf8
"Requires: Windows 10/11 + WSL, an Anthropic API key, and Claude Desktop." | Out-File $notesFile -Append -Encoding utf8

gh release view $tag --repo $Repo 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Creating GitHub Release $tag on $Repo..." -ForegroundColor Yellow
    gh release create $tag $exe --repo $Repo --title "Metis $Version" --notes-file $notesFile
} else {
    Write-Host ""
    Write-Host "Release $tag exists on $Repo — removing stale assets + uploading fresh exe..." -ForegroundColor Yellow
    # Remove the old per-variant installers (superseded by the single MetisSetup-$Version.exe)
    foreach ($stale in @("MetisSetup-full-$Version.exe","MetisSetup-standard-$Version.exe","MetisSetup-minimal-$Version.exe")) {
        gh release delete-asset $tag $stale --repo $Repo --yes 2>$null
    }
    gh release upload $tag $exe --repo $Repo --clobber
    gh release edit  $tag --repo $Repo --notes-file $notesFile
}

Write-Host ""
Write-Host "Done. https://github.com/$Repo/releases/tag/$tag" -ForegroundColor Green
