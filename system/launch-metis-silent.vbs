' launch-metis-silent.vbs
' Starts the Metis dashboard with no visible terminal windows.
' Use this as your desktop shortcut target instead of launch-dashboard.bat.
'
' To update your shortcut:
'   Right-click shortcut → Properties → Target → browse to this .vbs file

Dim WshShell, fso
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

Dim scriptDir
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Convert Windows path to WSL path (auto-detect default distro)
Dim oExec
Set oExec = WshShell.Exec("wsl.exe wslpath -u " & Chr(34) & scriptDir & Chr(34))
Dim wslDir
wslDir = Trim(oExec.StdOut.ReadAll())

If wslDir = "" Then
    MsgBox "Could not reach WSL. Make sure WSL (Ubuntu) is installed." & vbCrLf & _
           "Download from the Microsoft Store or run: wsl --install", 16, "Metis"
    WScript.Quit
End If

' Launch dashboard silently (windowStyle=0 hides the terminal)
WshShell.Run "wsl.exe -- bash " & Chr(34) & wslDir & "/app-py/run.sh" & Chr(34), 0, False

' Wait for uvicorn to bind (adjust if your machine is slower)
WScript.Sleep 4000

' Open dashboard in default browser
WshShell.Run "http://127.0.0.1:8080", 1, False

Set WshShell = Nothing
Set fso      = Nothing
