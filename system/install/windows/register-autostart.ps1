# register-autostart.ps1
# Register the Metis Dashboard to auto-start at login AND stay alive via a
# periodic heartbeat. The VBS script is idempotent — if uvicorn is already
# running, it exits instantly. The heartbeat recovers from sleep/wake, WSL
# crashes, and any other unexpected shutdown.
#
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

# Trigger 1: at logon for current user (immediate cold start)
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Trigger 2: periodic heartbeat — every 5 minutes, forever.
# This is the resilience layer: recovers from sleep/wake, WSL shutdown,
# supervisor crash, or anything else that kills the dashboard.
# The VBS script checks pgrep first and exits instantly if already running,
# so the cost is ~200ms of wsl.exe invocation when healthy.
$triggerHeartbeat = New-ScheduledTaskTrigger -Once `
    -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes 5)
# Make the repetition last indefinitely (PowerShell quirk: set duration to 0 = forever)
$triggerHeartbeat.Repetition.StopAtDurationEnd = $false

# Settings: allow start on battery, don't stop if switching to battery,
# start if the trigger was missed, don't start a second instance if already running
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

# Register with BOTH triggers
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger @($triggerLogon, $triggerHeartbeat) `
    -Settings $settings `
    -Description "Start the Metis Research Cortex dashboard at login and keep it alive with a 5-minute heartbeat. Recovers from sleep/wake, WSL crashes, and unexpected shutdowns. No browser window is opened." `
    -RunLevel Limited

Write-Host ""
Write-Host "Task registered: $taskName" -ForegroundColor Green
Write-Host "  Action:    wscript.exe `"$vbsPath`""
Write-Host "  Trigger 1: At logon (cold start)"
Write-Host "  Trigger 2: Every 5 minutes (heartbeat / recovery)"
Write-Host "  Settings:  Battery OK, no duplicate instances"
Write-Host ""
Write-Host "Verify in Task Scheduler: taskschd.msc -> Task Scheduler Library -> $taskName"
