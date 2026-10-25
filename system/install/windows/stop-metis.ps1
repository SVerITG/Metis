# Stop every running copy of Metis for this person: the server Claude Desktop
# started, the dashboard, a self-check. The uninstaller runs this first,
# because Windows will not delete files a running program has loaded.
$ErrorActionPreference = "SilentlyContinue"
$own = Join-Path $env:LOCALAPPDATA "Metis"
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object {
        ("$($_.CommandLine)" -match "metis_mcp|uvicorn main:app|metis_verify") -or
        ("$($_.ExecutablePath)".StartsWith($own, [StringComparison]::OrdinalIgnoreCase))
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
exit 0
