<#
.SYNOPSIS
    download_vendor_python.ps1 — Pre-download Python embeddable zip for offline bundling.

.DESCRIPTION
    Downloads the Python 3.11 embeddable package (for Windows x64) and saves it
    as vendor/python-embed.zip so the Inno Setup installer can bundle it.

    Run this ONCE on a machine with internet access before compiling the installer.

    Also downloads get-pip.py for fully offline pip bootstrap.

.EXAMPLE
    .\download_vendor_python.ps1
    # Output: system/install/vendor/python-embed.zip (~9 MB)
    #         system/install/vendor/get-pip.py
#>

$VendorDir  = Join-Path $PSScriptRoot "vendor"
$PyVersion  = "3.11.9"
$PyUrl      = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-amd64.zip"
$GetPipUrl  = "https://bootstrap.pypa.io/get-pip.py"

New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null

$embedDest = Join-Path $VendorDir "python-embed.zip"
$pipDest   = Join-Path $VendorDir "get-pip.py"

Write-Host "Downloading Python $PyVersion embeddable package…" -ForegroundColor Cyan
Invoke-WebRequest -Uri $PyUrl -OutFile $embedDest -UseBasicParsing
$sizeMB = (Get-Item $embedDest).Length / 1MB
Write-Host "  ✓ python-embed.zip  ($([math]::Round($sizeMB,1)) MB)" -ForegroundColor Green

Write-Host "Downloading get-pip.py…" -ForegroundColor Cyan
Invoke-WebRequest -Uri $GetPipUrl -OutFile $pipDest -UseBasicParsing
Write-Host "  ✓ get-pip.py" -ForegroundColor Green

Write-Host "`nVendor files ready in: $VendorDir" -ForegroundColor Green
Write-Host "Compile the installer next: ISCC.exe installer\metis-setup.iss"
