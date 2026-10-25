' launch-dashboard-silent.vbs
' Starts the Metis dashboard silently (no visible terminal window).
' Place a shortcut to this file on the desktop or in the Windows Startup folder.

Dim WshShell, fso
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

Dim scriptDir
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Dim batPath
batPath = fso.BuildPath(scriptDir, "run-dashboard.bat")

If Not fso.FileExists(batPath) Then
    MsgBox "Metis launcher not found: " & batPath & Chr(13) & Chr(10) & _
           "Please re-install Metis.", 16, "Metis"
    WScript.Quit
End If

' Run the batch silently (windowStyle=0 = hidden)
' /background (the log-on task): start it, but open no browser window.
Dim extra
extra = ""
If WScript.Arguments.Count > 0 Then extra = " " & WScript.Arguments(0)

WshShell.Run Chr(34) & batPath & Chr(34) & extra, 0, False

' run-dashboard.bat handles the wait and browser open — no duplicate needed here

Set WshShell = Nothing
Set fso      = Nothing
