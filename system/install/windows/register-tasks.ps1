<#
.SYNOPSIS
    Schedule Metis's two background tasks for this person. Safe to run again.

.DESCRIPTION
    "Metis self-check"  daily at 09:30 and at log-on: the install doctor, which
                        checks everything and repairs what it can.
    "Metis dashboard"   at log-on: starts the dashboard hidden, so the morning
                        news and literature scans run (only with the dashboard).

    Both run as the person, hidden, and also on battery: Task Scheduler's
    default refuses to start a task on battery, so on a laptop it silently
    never runs. The one place these tasks are defined — install.ps1 calls this,
    and so does the install doctor when it repairs a missing task.

    Exit 0 when every requested task is registered, 1 otherwise.
#>
param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [ValidateSet("all", "selfcheck", "dashboard")][string]$Only = "all",
    [switch]$Stage1Only
)
$ErrorActionPreference = "Stop"

$py = Join-Path $env:LOCALAPPDATA "Metis\venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) { $py = Join-Path $InstallDir "system\mcp-server\.venv-win\Scripts\pythonw.exe" }
$hasDashboard = (-not $Stage1Only) -and (Test-Path (Join-Path $InstallDir "system\app-py\main.py"))

function Register-MetisTask {
    param([string]$Name, [string]$Execute, [string]$Arguments, [string]$Description,
          [object]$Daily = $null, [string]$LogonDelay = "PT5M", [int]$LimitHours = 1)
    $action = New-ScheduledTaskAction -Execute $Execute -Argument $Arguments -WorkingDirectory $InstallDir
    $limit = if ($LimitHours -gt 0) { New-TimeSpan -Hours $LimitHours } else { New-TimeSpan -Seconds 0 }
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit $limit
    $triggers = @()
    if ($Daily) { $triggers += $Daily }
    try {
        $logon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
        $logon.Delay = $LogonDelay
        Register-ScheduledTask -TaskName $Name -Action $action -Trigger (@($triggers) + $logon) `
            -Settings $settings -Description $Description -Force | Out-Null
    }
    catch {
        # A log-on trigger can need rights a normal account lacks.
        if (-not $Daily) { throw }
        Register-ScheduledTask -TaskName $Name -Action $action -Trigger $Daily `
            -Settings $settings -Description $Description -Force | Out-Null
    }
}

$failed = 0
if ($Only -in @("all", "selfcheck")) {
    try {
        $verify = Join-Path $InstallDir "system\install\metis_verify.py"
        Register-MetisTask -Name "Metis self-check" -Execute $py -Arguments "`"$verify`" --fix --quiet" `
            -Daily (New-ScheduledTaskTrigger -Daily -At "09:30") `
            -Description "Checks that Metis works with your AI apps and repairs what it can. Result on the Metis dashboard."
        Write-Output "selfcheck: registered"
    }
    catch { Write-Output "selfcheck: $_"; $failed++ }
}
if ($Only -in @("all", "dashboard") -and $hasDashboard) {
    try {
        $vbs = Join-Path $InstallDir "system\install\windows\launch-dashboard-silent.vbs"
        Register-MetisTask -Name "Metis dashboard" -Execute "$env:WINDIR\System32\wscript.exe" `
            -Arguments "`"$vbs`" /background" -LogonDelay "PT1M" -LimitHours 0 `
            -Description "Starts the Metis dashboard in the background at log-on, so the morning news and literature scans run."
        Write-Output "dashboard: registered"
    }
    catch { Write-Output "dashboard: $_"; $failed++ }
}
if ($failed) { exit 1 } else { exit 0 }
