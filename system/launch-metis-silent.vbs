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

' Give run.sh a moment to choose a port and write the port file
WScript.Sleep 3000

' Read the port actually selected by run.sh (written to .metis-port before exec)
Dim port
port = "8080"
Dim oPort
Set oPort = WshShell.Exec("wsl.exe -- cat " & Chr(34) & wslDir & "/app-py/.metis-port" & Chr(34))
Dim portOut
portOut = Trim(oPort.StdOut.ReadAll())
If portOut <> "" Then port = portOut

Dim url
url = "http://127.0.0.1:" & port

' Metis's first start can take 10-30s (agents, scheduler, embedding model). Poll
' until the dashboard actually responds before opening the browser — a fixed wait
' opened it too early and showed "can't connect".
Dim http, i, ready
ready = False
For i = 1 To 40
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.SetTimeouts 1000, 1000, 2000, 2000
    http.Open "GET", url, False
    http.Send
    If Err.Number = 0 And http.Status >= 200 And http.Status < 600 Then
        ready = True
    End If
    On Error GoTo 0
    If ready Then Exit For
    WScript.Sleep 1000
Next

' Open dashboard in default browser (open anyway after the timeout — it will retry)
WshShell.Run url, 1, False

Set WshShell = Nothing
Set fso      = Nothing
