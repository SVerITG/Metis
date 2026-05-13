' launch-metis-silent.vbs
' Starts the Metis dashboard with no visible terminal windows.
' Use this as your desktop shortcut target instead of launch-dashboard.bat.
'
' To update your shortcut:
'   Right-click shortcut → Properties → Target → browse to this .vbs file

Dim WshShell, fso
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

' Determine this script's directory
Dim scriptDir
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Convert Windows path to WSL path
Dim oExec
Set oExec = WshShell.Exec("wsl.exe wslpath -u " & Chr(34) & scriptDir & Chr(34))
Dim wslDir
wslDir = Trim(oExec.StdOut.ReadAll())

If wslDir = "" Then
    MsgBox "Could not reach WSL. Make sure WSL (Ubuntu) is installed.", 16, "Metis"
    WScript.Quit
End If

' Launch the dashboard server silently (windowStyle=0 = hidden)
WshShell.Run "wsl.exe -d Ubuntu-24.04 -- bash " & Chr(34) & wslDir & "/app-py/run.sh" & Chr(34), 0, False

' Wait for uvicorn to be ready
WScript.Sleep 5000

' Open browser
WshShell.Run "http://127.0.0.1:8080", 1, False

Set WshShell = Nothing
Set fso      = Nothing
