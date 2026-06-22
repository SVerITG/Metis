# register-autostart.ps1
# Register the Metis Dashboard to auto-start at login via Windows Task Scheduler.
# Run once: powershell -ExecutionPolicy Bypass -File register-autostart.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbsPath   = Join-Path $scriptDir "autostart-dashboard.vbs"

if (-not (Test-Path $vbsPath)) {
    Write-Error "autostart-dashboard.vbs not found at: $vbsPath"
    exit 1
}

$taskName = "Metis Dashboard Autostart"

# Remove existing task if present (idempotent)
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create the action: wscript.exe runs the VBS silently
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`""

# Trigger: at logon for current user
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Settings: allow start on battery, don't stop if switching to battery,
# start if the trigger was missed (e.g. laptop was off at login time)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

# Register
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Start the Metis Research Cortex dashboard at login so scheduled jobs (morning brief, news scan, library index, etc.) fire on time. No browser window is opened." `
    -RunLevel Limited

Write-Host ""
Write-Host "Task registered: $taskName" -ForegroundColor Green
Write-Host "  Action:  wscript.exe `"$vbsPath`""
Write-Host "  Trigger: At logon"
Write-Host ""
Write-Host "Verify in Task Scheduler: taskschd.msc -> Task Scheduler Library -> $taskName"
