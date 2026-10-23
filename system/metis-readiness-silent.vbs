' metis-readiness-silent.vbs
' Runs the Metis readiness check inside WSL with no visible window.
' Registered as a Windows scheduled task by tools/install-readiness-schedule.sh.
'
' Arguments:  <WSL distro name>  <Linux path to the Metis root>
'
' The dashboard is started first, the same way launch-metis-silent.vbs does it,
' because WSL stops a distro once its last wsl.exe exits: a dashboard started
' from inside the short-lived check would die with it. run-dashboard.sh exits at
' once when the dashboard is already serving, so this is safe to repeat.

Dim sh, distro, root, wsl
Set sh = CreateObject("WScript.Shell")
If WScript.Arguments.Count < 2 Then WScript.Quit 2
distro = WScript.Arguments(0)
root   = WScript.Arguments(1)
wsl    = "wsl.exe -d " & Chr(34) & distro & Chr(34) & " -e bash -lc "

sh.Run wsl & Chr(34) & "cd '" & root & "/system/app-py' && if [ -f run.sh ]; then exec bash run.sh; else exec bash run-dashboard.sh; fi" & Chr(34), 0, False

sh.Run wsl & Chr(34) & "bash '" & root & "/tools/metis-readiness.sh' --fix >> ~/.local/share/metis-mcp/readiness.log 2>&1" & Chr(34), 0, True
