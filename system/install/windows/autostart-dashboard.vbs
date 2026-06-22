' autostart-dashboard.vbs
' Starts the Metis dashboard headlessly at login (no browser, no terminal).
' Intended for Windows Task Scheduler — ensures the scheduler jobs
' (morning scan, daily brief, etc.) fire on time even before you open Metis.
'
' What it does:
'   1. Checks if the dashboard is already running (avoids double-launch)
'   2. Starts run.sh via WSL with window hidden
'   3. Exits silently — no browser opened
'
' To use manually: wscript.exe "path\to\autostart-dashboard.vbs"

Dim WshShell, fso
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

Dim scriptDir
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Navigate from system/install/windows/ up to the RC root, then into system/
Dim rcRoot
rcRoot = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))

' Convert to WSL path
Dim oExec
Set oExec = WshShell.Exec("wsl.exe wslpath -u " & Chr(34) & rcRoot & Chr(34))
Dim wslRoot
wslRoot = Trim(oExec.StdOut.ReadAll())

If wslRoot = "" Then
    ' WSL not reachable — exit silently (Task Scheduler doesn't need a popup)
    WScript.Quit
End If

' Check if a Metis uvicorn is already running — don't double-launch
Dim oCheck
Set oCheck = WshShell.Exec("wsl.exe -- bash -c ""pgrep -f 'uvicorn main:app' >/dev/null 2>&1 && echo RUNNING || echo STOPPED""")
Dim checkOut
checkOut = Trim(oCheck.StdOut.ReadAll())

If checkOut = "RUNNING" Then
    ' Dashboard already up — nothing to do
    WScript.Quit
End If

' Start the dashboard detached and hidden (windowStyle=0)
WshShell.Run "wsl.exe -- bash -c ""setsid nohup bash '" & wslRoot & "/app-py/run.sh' </dev/null >/tmp/metis-dashboard.log 2>&1 & disown""", 0, False

Set WshShell = Nothing
Set fso      = Nothing
