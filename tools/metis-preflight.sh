#!/bin/bash
# metis-preflight.sh — Keep this computer's Metis current, automatically.
#
# WHY THIS EXISTS
#   Metis is worked on from two computers. Git alone does not make a machine
#   "up to date": the MCP server runs an INSTALLED COPY of the package in a
#   venv, so pulled source is inert until it is reinstalled. On 2026-07-14 the
#   repo was current but the running server was six days stale — 7 files behind,
#   silently missing the memory-gateway / session-memory / user-profile work.
#
#   This script closes that gap at the one choke point every client passes
#   through: run.sh, which launches the MCP server for BOTH Claude Code and
#   Claude Desktop. Because the sync runs BEFORE the final `exec python`, a
#   reinstall lands and the fresh code is what actually gets loaded.
#
# MODES
#   (no args)   sync   — fetch, fast-forward, reinstall if stale. Used by run.sh.
#   --report           — read-only summary on stdout. Used by the SessionStart hook.
#   --end              — push committed work so the OTHER computer can see it.
#
# HARD RULES
#   * stdout is sacred in sync mode. MCP speaks JSON-RPC over stdio; a single
#     stray byte on stdout corrupts the protocol. All chatter goes to stderr.
#   * Never fail the launch. Every path exits 0. A broken network must not be
#     able to stop Metis from starting.
#   * Never destructive. Fast-forward only, clean tree only, never auto-commit.
#   * Never push main to `origin`. origin/main is the GENERATED base shell
#     (main + build-base-shell.sh commit). The working remote is `metis-ph`.
#
# TUNING (env)
#   METIS_SYNC_INTERVAL_H   hours between network checks (default 4; 0 = always)
#   METIS_NO_AUTOPUSH=1     disable the --end auto-push (warn instead)
#   METIS_NO_PREFLIGHT=1    disable the whole thing

set -uo pipefail

STATE_DIR="$HOME/.local/share/metis-mcp"
STAMP="$STATE_DIR/.last-sync-check"
STATUS="$STATE_DIR/last-preflight.txt"
LOCK="$STATE_DIR/.preflight.lock"
INTERVAL_H="${METIS_SYNC_INTERVAL_H:-4}"
MODE="${1:-sync}"

log()    { echo "[metis-preflight] $*" >&2; }
status() { echo "$*" >> "$STATUS"; }

# Always exit 0 — a failed preflight must never block the MCP server from starting.
# But it must not do so SILENTLY: a bare `trap 'exit 0' ERR` swallows the failure
# whole, which is how the fresh-machine bug (an `ls` on a missing package aborting
# the script at line ~71) stayed invisible. Say where we died, then stand down.
trap 'echo "[metis-preflight] aborted at line $LINENO — continuing without sync" >&2; exit 0' ERR

[ "${METIS_NO_PREFLIGHT:-0}" = "1" ] && exit 0

# ── Resolve the repo root ────────────────────────────────────────────────────
# Priority: env var → marker file → this script's own location. The last one is
# the backstop that cannot go stale: this script lives at <root>/tools/, so it
# always knows where the repo is even when the marker was never written (which
# is exactly the state an older setup-mcp.sh leaves a machine in).
ROOT="${METIS_RC_ROOT:-}"
if [ -z "$ROOT" ] && [ -f "$STATE_DIR/.metis-rc-root" ]; then
    ROOT="$(tr -d '\r\n' < "$STATE_DIR/.metis-rc-root")"
fi
if [ -z "$ROOT" ] || [ ! -d "$ROOT/.git" ]; then
    ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
if [ ! -d "$ROOT/.git" ]; then
    log "no git repo found (looked at '$ROOT') — skipping preflight"
    exit 0
fi

VENV="$STATE_DIR/.venv"
# The installed package's server.py is our "last install" timestamp marker.
#
# `|| true` matters: under `set -o pipefail` + the ERR trap above, a failing `ls`
# (no package installed yet — exactly the fresh-machine case this script exists to
# fix) would fire the ERR trap and exit 0 RIGHT HERE, silently. The whole
# anti-stale-install mechanism would fail open on the one machine that needs it.
INSTALLED_MARKER="$(ls "$VENV"/lib/python*/site-packages/metis_mcp/server.py 2>/dev/null | head -1 || true)"
SRC_DIR="$ROOT/system/mcp-server/src"

git_q() { git -C "$ROOT" "$@" 2>/dev/null; }

# ── Is the installed copy behind the source? (cheap: ~0.25s stat walk) ───────
# A `git pull` rewrites file mtimes, so "any source .py newer than the installed
# server.py" is a reliable, fast staleness signal. Hashing all 69 files would be
# more precise but costs 2.6s on DrvFs (/mnt/c) — far too slow for every launch.
is_stale() {
    [ -z "$INSTALLED_MARKER" ] && return 0          # nothing installed at all
    [ -n "$(find "$SRC_DIR" -name '*.py' -newer "$INSTALLED_MARKER" -print -quit 2>/dev/null)" ]
}

# ── Report mode: read-only, prints to STDOUT for the SessionStart hook ───────
if [ "$MODE" = "--report" ]; then
    branch="$(git_q rev-parse --abbrev-ref HEAD)"
    behind="$(git_q rev-list --count "HEAD..metis-ph/$branch" 2>/dev/null || echo 0)"
    ahead="$(git_q rev-list --count "metis-ph/$branch..HEAD" 2>/dev/null || echo 0)"
    dirty="$(git_q status --porcelain | wc -l)"

    if is_stale; then
        echo "METIS SYNC: the installed MCP server is STALE vs the source. Tell Stan to run /mcp and reconnect 'metis-rc' so the new code loads."
    fi
    [ "${behind:-0}" -gt 0 ] && echo "METIS SYNC: this computer is $behind commit(s) BEHIND the other computer (metis-ph/$branch). Offer to pull."
    [ "${ahead:-0}"  -gt 0 ] && echo "METIS SYNC: $ahead commit(s) on this computer are NOT pushed. Remind Stan to push before switching computers."
    [ "${dirty:-0}"  -gt 0 ] && echo "METIS SYNC: $dirty uncommitted file(s) in the working tree."
    exit 0
fi

# ── End-of-session: get this computer's work onto the other computer ─────────
# The preflight on computer B cannot recover work that computer A never pushed.
# This is the other half of the loop.
if [ "$MODE" = "--end" ]; then
    # Daily canonical DB snapshot → OneDrive. The live DB is per-machine and does
    # NOT sync between computers (WAL + OneDrive corrupts it — see
    # data-persistence-strategy.md §4). This snapshot is the only way this machine's
    # memory becomes recoverable, and the only way the other computer can see that a
    # divergent DB exists. Backgrounded: a 165 MB copy must not stall session exit.
    DB_STAMP="$STATE_DIR/.last-db-backup"
    db_last=0
    [ -f "$DB_STAMP" ] && db_last="$(cat "$DB_STAMP" 2>/dev/null || echo 0)"
    if [ $(( ($(date +%s) - db_last) / 3600 )) -ge 20 ]; then
        if [ -x "$VENV/bin/python3" ] && [ -f "$ROOT/tools/backup-canonical.py" ]; then
            date +%s > "$DB_STAMP"
            log "snapshotting the database to OneDrive (daily, in the background)…"
            nohup "$VENV/bin/python3" "$ROOT/tools/backup-canonical.py" \
                >"$STATE_DIR/last-db-backup.log" 2>&1 &
        fi
    fi

    branch="$(git_q rev-parse --abbrev-ref HEAD)"
    [ "$branch" != "main" ] && exit 0
    if [ -n "$(git_q status --porcelain)" ]; then
        log "uncommitted changes on main — NOT pushing. Commit them so the other computer can see them."
        exit 0
    fi
    if [ "$(git_q rev-list --count metis-ph/main..HEAD 2>/dev/null || echo 0)" -gt 0 ]; then
        if [ "${METIS_NO_AUTOPUSH:-0}" = "1" ]; then
            log "unpushed commits on main — push them before switching computers."
        else
            # metis-ph ONLY. origin/main is the generated base shell; pushing
            # main there would clobber the build-base-shell.sh commit.
            log "pushing committed work to metis-ph so the other computer sees it…"
            timeout 60 git -C "$ROOT" push metis-ph main >&2 2>&1 \
                && log "pushed." || log "push failed — do it manually."
        fi
    fi
    exit 0
fi

# ── Sync mode (default) — runs from run.sh on every MCP launch ───────────────
# Only one preflight at a time; concurrent clients (Code + Desktop) must not
# race each other into a double reinstall.
exec 9>"$LOCK"
flock -n 9 || { log "another preflight is running — skipping"; exit 0; }

: > "$STATUS"
status "checked: $(date '+%Y-%m-%d %H:%M:%S')"

pulled=0
branch="$(git_q rev-parse --abbrev-ref HEAD)"

# Network check, throttled — we do not need to hit GitHub on every reconnect.
now=$(date +%s)
last=0
[ -f "$STAMP" ] && last="$(cat "$STAMP" 2>/dev/null || echo 0)"
age_h=$(( (now - last) / 3600 ))

if [ "$INTERVAL_H" -eq 0 ] || [ "$age_h" -ge "$INTERVAL_H" ]; then
    log "checking metis-ph for work from the other computer…"
    if timeout 25 git -C "$ROOT" fetch metis-ph --quiet 2>/dev/null; then
        echo "$now" > "$STAMP"
        behind="$(git_q rev-list --count "HEAD..metis-ph/$branch" 2>/dev/null || echo 0)"
        if [ "${behind:-0}" -gt 0 ]; then
            if [ "$branch" != "main" ]; then
                log "$behind commit(s) behind, but on branch '$branch' — not touching it."
                status "behind: $behind (branch $branch — not auto-pulled)"
            elif [ -n "$(git_q status --porcelain)" ]; then
                log "$behind commit(s) behind but the working tree is dirty — NOT pulling."
                status "behind: $behind (BLOCKED — uncommitted changes)"
            elif git -C "$ROOT" merge --ff-only "metis-ph/$branch" >/dev/null 2>&1; then
                log "pulled $behind commit(s) from the other computer."
                status "pulled: $behind commit(s) from metis-ph/$branch"
                pulled=1
            else
                log "cannot fast-forward (local commits diverge) — resolve by hand."
                status "behind: $behind (BLOCKED — diverged)"
            fi
        else
            status "git: up to date with metis-ph/$branch"
        fi
    else
        log "could not reach metis-ph (offline?) — continuing with local code."
        status "git: offline, not checked"
    fi
else
    status "git: skipped (checked ${age_h}h ago, interval ${INTERVAL_H}h)"
fi

# ── The step that actually matters: is the RUNNING code the CURRENT code? ────
if is_stale; then
    log "installed MCP server is behind the source — reinstalling…"
    # reinstall-mcp.sh prints to stdout; redirect it or it corrupts JSON-RPC.
    if bash "$ROOT/tools/reinstall-mcp.sh" >&2 2>&1; then
        log "reinstalled — the server about to start is running current code."
        status "mcp: REINSTALLED (was stale)"
    else
        log "reinstall FAILED — server will start on the old code."
        status "mcp: reinstall FAILED"
    fi
else
    status "mcp: installed copy matches source"
fi

# ── If we pulled dashboard code, the dashboard service needs a restart ───────
# (The dashboard reads source directly — no reinstall — but it must re-exec.)
if [ "$pulled" -eq 1 ]; then
    if systemctl --user is-active metis-dashboard >/dev/null 2>&1; then
        systemctl --user restart metis-dashboard >/dev/null 2>&1 \
            && { log "restarted the dashboard on the new code."; status "dashboard: restarted"; }
    fi
fi

exit 0
