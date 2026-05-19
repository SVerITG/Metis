# create_shortcut.ps1
# Creates a Desktop shortcut and Start Menu entry for Metis.
# Also converts Metis_github.png to Metis.ico so the brain icon shows correctly.
#
# Run once:
#   powershell -ExecutionPolicy Bypass -File "create_shortcut.ps1"

$AppDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatFile   = Join-Path $AppDir "launch_metis.bat"
$RootDir   = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $AppDir)))
$PngFile   = Join-Path $RootDir "Metis_github.png"
$IcoFile   = Join-Path $AppDir "Metis.ico"

# ── Convert PNG → ICO using System.Drawing ──────────────────────────────────
if (Test-Path $PngFile) {
    try {
        Add-Type -AssemblyName System.Drawing
        $png = [System.Drawing.Image]::FromFile($PngFile)

        # Resize to 256x256 for best icon quality
        $bmp = New-Object System.Drawing.Bitmap(256, 256)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.DrawImage($png, 0, 0, 256, 256)
        $g.Dispose()
        $png.Dispose()

        # Write ICO: header (6 bytes) + directory entry (16 bytes) + BMP data
        $ms = New-Object System.IO.MemoryStream
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $bmp.Dispose()
        $pngBytes = $ms.ToArray()
        $ms.Dispose()

        $fs = [System.IO.File]::OpenWrite($IcoFile)
        $bw = New-Object System.IO.BinaryWriter($fs)
        # ICO header
        $bw.Write([uint16]0)       # reserved
        $bw.Write([uint16]1)       # type: icon
        $bw.Write([uint16]1)       # image count
        # Directory entry
        $bw.Write([byte]0)         # width  (0 = 256)
        $bw.Write([byte]0)         # height (0 = 256)
        $bw.Write([byte]0)         # colour count
        $bw.Write([byte]0)         # reserved
        $bw.Write([uint16]1)       # colour planes
        $bw.Write([uint16]32)      # bits per pixel
        $bw.Write([uint32]$pngBytes.Length)  # size of image data
        $bw.Write([uint32]22)      # offset to image data (6+16)
        $bw.Write($pngBytes)
        $bw.Close()
        $fs.Close()
        Write-Host "Brain icon created: $IcoFile" -ForegroundColor Cyan
    } catch {
        Write-Host "Icon conversion failed: $_" -ForegroundColor Yellow
        $IcoFile = $null
    }
} else {
    Write-Host "PNG not found at $PngFile — shortcuts will use default icon" -ForegroundColor Yellow
    $IcoFile = $null
}

# ── Helper: create one shortcut ──────────────────────────────────────────────
function New-MetisShortcut {
    param([string]$Path, [string]$Description)
    $Shell    = New-Object -ComObject WScript.Shell
    $sc       = $Shell.CreateShortcut($Path)
    $sc.TargetPath       = $BatFile
    $sc.WorkingDirectory = $AppDir
    $sc.Description      = $Description
    $sc.WindowStyle      = 1
    if ($IcoFile -and (Test-Path $IcoFile)) {
        $sc.IconLocation = "$IcoFile,0"
    }
    $sc.Save()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($Shell) | Out-Null
}

# ── Desktop shortcut ─────────────────────────────────────────────────────────
$Desktop      = [System.Environment]::GetFolderPath("Desktop")
$DesktopLink  = Join-Path $Desktop "Metis.lnk"
New-MetisShortcut -Path $DesktopLink -Description "Open Metis"
Write-Host "Desktop shortcut created: $DesktopLink" -ForegroundColor Green

# ── Start Menu shortcut ──────────────────────────────────────────────────────
$StartMenu    = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$StartLink    = Join-Path $StartMenu "Metis.lnk"
New-MetisShortcut -Path $StartLink -Description "Open Metis"
Write-Host "Start Menu shortcut created: $StartLink" -ForegroundColor Green

Write-Host ""
Write-Host "Done! You can now:" -ForegroundColor Cyan
Write-Host "  - Double-click 'Metis' on your desktop"
Write-Host "  - Search 'Metis' in the Start Menu"
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
