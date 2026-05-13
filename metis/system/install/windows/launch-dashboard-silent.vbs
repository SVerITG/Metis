' launch-dashboard-silent.vbs
' Starts the Metis dashboard silently (no visible terminal).
' Use this as the desktop shortcut target after Windows-native install.

Dim WshShell, fso
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

Dim scriptDir
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Path to the batch launcher (two folders up: windows/ -> install/ -> system/ -> Metis root)
Dim batPath
batPath = fso.BuildPath(scriptDir, "run-dashboard.bat")

If Not fso.FileExists(batPath) Then
    MsgBox "Dashboard launcher not found: " & batPath, 16, "Metis"
    WScript.Quit
End If

' Run the batch silently (windowStyle=0)
WshShell.Run Chr(34) & batPath & Chr(34), 0, False

' Wait for uvicorn to bind
WScript.Sleep 5000

' Open browser
WshShell.Run "http://127.0.0.1:8000", 1, False

Set WshShell = Nothing
Set fso      = Nothing
