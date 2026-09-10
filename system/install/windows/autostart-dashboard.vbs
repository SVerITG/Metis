' autostart-dashboard.vbs
' Keeps Metis correct on this computer — at logon AND every 5 minutes.
'
' WHY THIS RUNS FROM WINDOWS, NOT FROM INSIDE WSL
'   WSL does not run when the computer starts, and it cannot resurrect itself.
'   A systemd USER service cannot help either: on this machine user@1000.service
'   fails to start ("Failed to spawn executor: Device or resource busy"), so a
'   service "enabled" inside it never actually runs. Supervision therefore has to
'   live OUTSIDE Linux — here, driven by Windows Task Scheduler.
'
' WHAT IT CALLS
'   tools/metis-boot.sh — idempotent, ~0.5s when everything is healthy. It:
'     1. fast-forwards the code from the other computer
'     2. reinstalls the MCP server if the venv copy is behind the source
'     3. makes sure the dashboard is actually SERVING (HTTP 200), not just running
'
' Registered by register-autostart.ps1 (at-logon + 5-minute heartbeat).
' To run manually: wscript.exe "path\to\autostart-dashboard.vbs"

Dim WshShell, fso
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

Dim scriptDir
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' scriptDir = <repo>\system\install\windows  →  three levels up is the repo root.
Dim repoRoot
repoRoot = fso.GetParentFolderName(fso.GetParentFolderName(fso.GetParentFolderName(scriptDir)))

' Translate the Windows path to a WSL path — WITHOUT LAUNCHING ANYTHING.
'
' THIS IS THE BLACK WINDOW. Reported 2026-09-10: "black screens that pop up and
' disappear, during which I cannot continue to work." This script runs every five
' minutes, and it used to call
'
'     WshShell.Exec("wsl.exe wslpath -u ...")
'
' to turn the repo path into a WSL path. `.Exec` has NO window-style parameter —
' it always creates a visible console. So every five minutes a black window
' appeared, took keyboard focus, and vanished. The real work on the last line has
' always been hidden (`.Run cmd, 0, True`, where 0 means hidden); it was this
' one-line helper that flashed.
'
' A drive path needs no process at all: C:\Users\x → /mnt/c/Users/x is string
' work. That removes the window AND the process spawn, so the heartbeat is
' cheaper as well as invisible. Anything unusual (a UNC share, a mapped drive)
' falls through to wslpath, run HIDDEN via a temp file — correctness kept for the
' odd case without paying a visible window in the normal one.
Dim wslRoot
wslRoot = ""
If Mid(repoRoot, 2, 1) = ":" Then
    wslRoot = "/mnt/" & LCase(Left(repoRoot, 1)) & Replace(Mid(repoRoot, 3), "\", "/")
Else
    Dim tmpFile, ts, shellCmd
    tmpFile = fso.GetSpecialFolder(2) & "\metis-wslpath.txt"
    ' cmd /c is needed for the redirect; 0 keeps it hidden, True waits for it.
    shellCmd = "cmd /c wsl.exe wslpath -u " & Chr(34) & repoRoot & Chr(34) & _
               " > " & Chr(34) & tmpFile & Chr(34)
    On Error Resume Next
    WshShell.Run shellCmd, 0, True
    If fso.FileExists(tmpFile) Then
        Set ts = fso.OpenTextFile(tmpFile, 1)
        If Not ts.AtEndOfStream Then wslRoot = ts.ReadAll()
        ts.Close
        fso.DeleteFile tmpFile, True
    End If
    On Error Goto 0
End If

' CR/LF must be stripped explicitly. `wslpath` terminates its output with a
' newline, and VBScript's Trim() removes only SPACES — not vbCr/vbLf. Leaving
' them in embeds a literal newline in the middle of the command, so bash gets
'   /mnt/c/…/Research Cortex\n/tools/metis-boot.sh  →  "No such file or directory"
' and the autostart silently does nothing. An earlier version of this script had
' exactly that bug, which is why the dashboard was never up after a reboot.
wslRoot = Replace(wslRoot, vbCr, "")
wslRoot = Replace(wslRoot, vbLf, "")
wslRoot = Trim(wslRoot)

If wslRoot = "" Then
    ' WSL not reachable — exit silently (Task Scheduler must not pop a dialog).
    WScript.Quit
End If

' Run the boot check hidden, and WAIT for it (bWaitOnReturn = True).
'
' Do NOT background it inside WSL with `setsid nohup … &`. When wsl.exe exits,
' Windows tears down that invocation and the detached child dies with it — the
' script never even reached its 4th line (verified 2026-07-14: an empty
' /tmp/metis-boot.log and no lock file). Staying attached keeps wsl.exe alive for
' the duration, which is what actually lets the work complete.
'
' Cost: ~0.5s when Metis is healthy (the normal case), up to ~1 min on a cold
' start. Task Scheduler is configured MultipleInstances=IgnoreNew, so a slow run
' simply causes the next heartbeat to be skipped rather than pile up.
Dim cmd
cmd = "wsl.exe -- bash -lc ""bash '" & wslRoot & "/tools/metis-boot.sh' " & _
      "</dev/null >/tmp/metis-boot.log 2>&1"""

WshShell.Run cmd, 0, True

Set WshShell = Nothing
Set fso      = Nothing
