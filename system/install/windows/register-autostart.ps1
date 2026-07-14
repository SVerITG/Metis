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

# Register with BOTH triggers.
# -ErrorAction Stop is essential: without it a "Access is denied" from a managed
# /corporate machine only writes a non-terminating error, the script sails past it
# and still prints "Task registered" — so the supervision looks installed when it
# is not. That false success is exactly why the dashboard appeared "fixed" for
# months while nothing was actually watching it (found 2026-07-14).
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger @($triggerLogon, $triggerHeartbeat) `
        -Settings $settings `
        -Description "Start the Metis Research Cortex dashboard at login and keep it alive with a 5-minute heartbeat. Recovers from sleep/wake, WSL crashes, and unexpected shutdowns. No browser window is opened." `
        -RunLevel Limited `
        -ErrorAction Stop | Out-Null
}
catch {
    Write-Host ""
    Write-Host "FAILED to register '$taskName': $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "This machine's policy may block at-logon tasks. Fallback that DOES work" -ForegroundColor Yellow
    Write-Host "without elevation (verified on 5XLQDJ4) — a 5-minute heartbeat only:" -ForegroundColor Yellow
    Write-Host "  schtasks /create /tn `"Metis Heartbeat`" /tr `"wscript.exe '$vbsPath'`" /sc minute /mo 5 /f"
    Write-Host ""
    Write-Host "Logon start is then covered by the Startup-folder shortcut." -ForegroundColor Yellow
    exit 1
}

# Prove it exists rather than assuming the call worked.
$check = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $check) {
    Write-Host "Register-ScheduledTask reported no error but the task is absent." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Task registered and verified present: $taskName" -ForegroundColor Green
Write-Host "  Action:    wscript.exe `"$vbsPath`""
Write-Host "  Trigger 1: At logon (cold start)"
Write-Host "  Trigger 2: Every 5 minutes (heartbeat / recovery)"
Write-Host "  Settings:  Battery OK, no duplicate instances"
Write-Host "  State:     $($check.State)"
Write-Host ""
Write-Host "Verify in Task Scheduler: taskschd.msc -> Task Scheduler Library -> $taskName"
