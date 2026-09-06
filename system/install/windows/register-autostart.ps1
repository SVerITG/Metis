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
    Write-Host "Register-ScheduledTask failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Retrying via schtasks /xml — managed policy usually blocks the cmdlet, not this." -ForegroundColor Yellow

    # NEVER fall back to a bare `schtasks /create /sc minute /mo 5`. That is how a
    # machine ends up looking supervised while it is not: schtasks.exe defaults
    # DisallowStartIfOnBatteries to TRUE, and there is NO command-line switch to
    # turn it off — only /xml can set it. On a laptop that means the heartbeat stops
    # the moment the lid is unplugged, which is most of the time. Found 2026-09-06
    # after a dashboard outage: the task registered on 2026-07-14 by exactly that
    # fallback had not run once in the 8 hours since the machine went to battery.
    #
    # The XML is generated here rather than shipped as a file because it embeds the
    # current user's SID and home path — that must never land in the repository.
    $sid = ([Security.Principal.WindowsIdentity]::GetCurrent()).User.Value
    $xmlPath = Join-Path $env:TEMP "metis-heartbeat.xml"
    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <URI>\$taskName</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>$sid</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Repetition><Interval>PT5M</Interval></Repetition>
      <Enabled>true</Enabled>
    </TimeTrigger>
    <LogonTrigger><Enabled>true</Enabled><UserId>$sid</UserId></LogonTrigger>
    <SessionStateChangeTrigger>
      <Enabled>true</Enabled><UserId>$sid</UserId><StateChange>SessionUnlock</StateChange>
    </SessionStateChangeTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>wscript.exe</Command>
      <Arguments>"$vbsPath"</Arguments>
    </Exec>
  </Actions>
</Task>
"@
    [IO.File]::WriteAllText($xmlPath, $xml, [Text.Encoding]::Unicode)
    & schtasks.exe /create /tn $taskName /xml $xmlPath /f | Out-Null
    Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue

    if (-not (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "Both registration paths failed — NOTHING is supervising Metis." -ForegroundColor Red
        Write-Host "Open taskschd.msc and add the task by hand, or ask for help." -ForegroundColor Red
        exit 1
    }
    Write-Host "Registered via XML fallback: battery-safe, logon + unlock + 5-minute." -ForegroundColor Green
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
