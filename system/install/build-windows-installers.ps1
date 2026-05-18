# build-windows-installers.ps1
# Compiles the 3 Metis Windows exe installers locally and uploads them to GitHub.
#
# Usage (from PowerShell on Windows):
#   cd "C:\Users\<username>\OneDrive - ITG\Documents\7. Software\Research Cortex\metis\system\install"
#   .\build-windows-installers.ps1
#
# Optional — skip GitHub upload, just build the exe files:
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

# ── 2. Compile three variants ─────────────────────────────────────────────────
$types = @("full", "standard", "minimal")
foreach ($type in $types) {
    Write-Host ""
    Write-Host "Compiling $type installer..." -ForegroundColor Yellow
    & $iscc /DDefaultType=$type /DMyAppVersion=$Version $IssFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ISCC failed for type=$type (exit code $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

# ── 3. List output files ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "Built installers:" -ForegroundColor Green
Get-ChildItem "$DistDir\*.exe" | ForEach-Object {
    $mb = [math]::Round($_.Length / 1MB, 1)
    Write-Host "  $($_.Name)  ($mb MB)"
}

if ($SkipUpload) {
    Write-Host ""
    Write-Host "Done. Skipped GitHub upload (-SkipUpload)." -ForegroundColor Green
    exit 0
}

# ── 4. Upload to GitHub Release ───────────────────────────────────────────────
$ghCmd = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghCmd) {
    Write-Host ""
    Write-Host "gh CLI not found — upload manually from: $DistDir" -ForegroundColor Yellow
    exit 0
}

$tag  = "v$Version"
$exes = Get-ChildItem "$DistDir\MetisSetup-*-$Version.exe" | Select-Object -ExpandProperty FullName

# Write release notes to a temp file (avoids here-string indentation issues)
$notesFile = Join-Path $env:TEMP "metis-release-notes.txt"
"Metis Research Cortex $Version - base release." | Out-File $notesFile -Encoding utf8
""                                               | Out-File $notesFile -Append -Encoding utf8
"Windows Installers:"                            | Out-File $notesFile -Append -Encoding utf8
"  MetisSetup-full-$Version.exe     - Core + dashboard + Statistics course (recommended)" | Out-File $notesFile -Append -Encoding utf8
"  MetisSetup-standard-$Version.exe - Core + dashboard"                                  | Out-File $notesFile -Append -Encoding utf8
"  MetisSetup-minimal-$Version.exe  - Core (MCP + agents) only"                          | Out-File $notesFile -Append -Encoding utf8
""                                               | Out-File $notesFile -Append -Encoding utf8
"Requires: Windows 10+, Python 3.10+, Anthropic API key, Claude Desktop." | Out-File $notesFile -Append -Encoding utf8

# Check if release already exists
gh release view $tag --repo SVerITG/Metis 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Creating GitHub Release $tag..." -ForegroundColor Yellow
    gh release create $tag @exes `
        --repo SVerITG/Metis `
        --title "Metis $Version" `
        --notes-file $notesFile
} else {
    Write-Host ""
    Write-Host "Release $tag exists — uploading assets..." -ForegroundColor Yellow
    foreach ($exe in $exes) {
        gh release upload $tag $exe --repo SVerITG/Metis --clobber
    }
}

Write-Host ""
Write-Host "Done. https://github.com/SVerITG/Metis/releases/tag/$tag" -ForegroundColor Green
