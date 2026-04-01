' launch_monia_background.vbs
' Launches the Monia dashboard silently — no console window.
' Use for Windows startup auto-launch.
'
' To auto-start at login:
'   1. Press Win+R, type: shell:startup, press Enter
'   2. Copy a SHORTCUT to this .vbs file into that folder
'
' Dashboard available at: http://localhost:3838

Dim WshShell, fso
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

' Folder where this script lives (= metis-dashboard folder)
Dim scriptDir
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Dim launchR
launchR = scriptDir & "\launch.R"

If Not fso.FileExists(launchR) Then
  MsgBox "launch.R not found at: " & launchR, 16, "Monia"
  WScript.Quit
End If

' Find Rscript.exe
Dim rscript
rscript = ""
Dim candidates(6)
candidates(0) = "C:\Program Files\R\R-4.4.2\bin\Rscript.exe"
candidates(1) = "C:\Program Files\R\R-4.4.1\bin\Rscript.exe"
candidates(2) = "C:\Program Files\R\R-4.4.0\bin\Rscript.exe"
candidates(3) = "C:\Program Files\R\R-4.3.3\bin\Rscript.exe"
candidates(4) = "C:\Program Files\R\R-4.3.2\bin\Rscript.exe"
candidates(5) = "C:\Program Files\R\R-4.3.1\bin\Rscript.exe"

Dim i
For i = 0 To UBound(candidates)
  If fso.FileExists(candidates(i)) Then
    rscript = candidates(i)
    Exit For
  End If
Next

If rscript = "" Then
  MsgBox "Rscript.exe not found. Please edit launch_monia_background.vbs with the correct R path.", 16, "Monia"
  WScript.Quit
End If

' Launch silently (windowStyle=0, bWaitOnReturn=False)
Dim cmd
cmd = """" & rscript & """ """ & launchR & """"
WshShell.Run cmd, 0, False

Set WshShell = Nothing
Set fso = Nothing
