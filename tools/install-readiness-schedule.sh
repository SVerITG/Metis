#!/bin/bash
# install-readiness-schedule.sh — run the Metis readiness check every day.
#
# On WSL it registers a Windows scheduled task, not a cron job: WSL is not
# running when nobody has opened it, so cron inside it would miss most mornings.
# The task runs even if the computer was off at the set time (it catches up at
# the next start), needs no administrator rights, and shows no window.
# On Linux and macOS it adds a crontab line.
#
# USAGE
#   bash tools/install-readiness-schedule.sh              # daily at 07:45
#   bash tools/install-readiness-schedule.sh --time 08:30
#   bash tools/install-readiness-schedule.sh --status
#   bash tools/install-readiness-schedule.sh --remove
#
# The verdict lands in system/config/readiness.json (shown on the dashboard's
# Today footer and Metis tab, and at the start of each Claude Code session) and
# outputs/readiness/<date>.md. The run log is ~/.local/share/metis-mcp/readiness.log.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK="Metis readiness check"
TAG="# metis-readiness"
AT="07:45"
MODE="install"

while [ $# -gt 0 ]; do
    case "$1" in
        --time)   AT="$2"; shift 2 ;;
        --status) MODE="status"; shift ;;
        --remove) MODE="remove"; shift ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
[[ "$AT" =~ ^([01][0-9]|2[0-3]):[0-5][0-9]$ ]] || { echo "--time must be HH:MM (24h)" >&2; exit 2; }

if grep -qi microsoft /proc/version 2>/dev/null; then
    PS="powershell.exe -NoProfile -NonInteractive -Command"
    case "$MODE" in
        status)
            $PS "Get-ScheduledTask -TaskName '$TASK' -ErrorAction SilentlyContinue | Get-ScheduledTaskInfo | Format-List TaskName,LastRunTime,LastTaskResult,NextRunTime" \
                | tr -d '\r' | grep -v '^$' || echo "not scheduled"
            ;;
        remove)
            $PS "Unregister-ScheduledTask -TaskName '$TASK' -Confirm:\$false -ErrorAction SilentlyContinue"
            echo "removed the Windows scheduled task '$TASK'"
            ;;
        install)
            DISTRO="${WSL_DISTRO_NAME:-}"
            [ -n "$DISTRO" ] || { echo "WSL_DISTRO_NAME is not set — run this from inside WSL" >&2; exit 1; }
            # Run the .vbs from a local Windows folder: Script Host can stop at a
            # security prompt for a script on a \\wsl.localhost network path.
            # Re-run this installer after changing the .vbs.
            LAD="$($PS "[Environment]::GetFolderPath('LocalApplicationData')" | tr -d '\r')"
            [ -n "$LAD" ] || { echo "could not find the Windows LocalAppData folder" >&2; exit 1; }
            mkdir -p "$(wslpath -u "$LAD")/Metis"
            cp "$ROOT/system/metis-readiness-silent.vbs" "$(wslpath -u "$LAD")/Metis/"
            VBS="$LAD\\Metis\\metis-readiness-silent.vbs"
            $PS "\
\$a = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '\"$VBS\" \"$DISTRO\" \"$ROOT\"'; \
\$t = New-ScheduledTaskTrigger -Daily -At '$AT'; \
\$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30); \
Register-ScheduledTask -TaskName '$TASK' -Action \$a -Trigger \$t -Settings \$s -Force \
  -Description 'Checks the Metis MCP server, dashboard, code and database are ready for work. Writes system/config/readiness.json.' | Out-Null"
            echo "scheduled: '$TASK' daily at $AT (Windows Task Scheduler, distro $DISTRO)"
            echo "run it now:  bash tools/metis-readiness.sh --fix"
            ;;
    esac
    exit 0
fi

# Linux / macOS: crontab
current="$(crontab -l 2>/dev/null || true)"
case "$MODE" in
    status)
        printf '%s\n' "$current" | grep -F "$TAG" || echo "not scheduled"
        ;;
    remove)
        printf '%s\n' "$current" | grep -vF "$TAG" | crontab -
        echo "removed the crontab entry"
        ;;
    install)
        line="${AT#*:} ${AT%%:*} * * * bash '$ROOT/tools/metis-readiness.sh' --fix >> \"\$HOME/.local/share/metis-mcp/readiness.log\" 2>&1 $TAG"
        { printf '%s\n' "$current" | grep -vF "$TAG" | grep -v '^$' || true; echo "$line"; } | crontab -
        echo "scheduled: daily at $AT (crontab)"
        echo "run it now:  bash tools/metis-readiness.sh --fix"
        ;;
esac
