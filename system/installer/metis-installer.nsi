;--------------------------------------------------------------
; Metis Research Cortex -- Windows Installer
; Build from WSL: bash build-installer.sh
; Requires: makensis (sudo apt install nsis)
;--------------------------------------------------------------

!include "MUI2.nsh"
!include "LogicLib.nsh"

;--- Info ---
Name "Metis Research Cortex"
Caption "Metis Research Cortex Setup"
OutFile "Metis-Installer.exe"
RequestExecutionLevel user
ShowInstDetails show
SetCompressor /SOLID lzma

;--- MUI2 appearance ---
!define MUI_ABORTWARNING
!define MUI_ABORTWARNING_TEXT "Are you sure you want to cancel the installation?"

!define MUI_WELCOMEPAGE_TITLE "Metis Research Cortex"
!define MUI_WELCOMEPAGE_TEXT "This installer will configure your Metis environment:$\r$\n$\r$\n  * Python virtual environment (WSL)$\r$\n  * MCP server + dashboard dependencies$\r$\n  * Database initialisation$\r$\n  * Desktop and Start Menu shortcuts$\r$\n$\r$\nPrerequisite: WSL (Windows Subsystem for Linux) must be installed.$\r$\nIf WSL is missing the installer will tell you what to do.$\r$\n$\r$\nSetup takes 2-5 minutes on first install."

!define MUI_INSTFILESPAGE_PROGRESSBAR colored

!define MUI_FINISHPAGE_TITLE "Metis is ready"
!define MUI_FINISHPAGE_TEXT "Installation complete.$\r$\n$\r$\nNext steps:$\r$\n  1. Restart Claude Desktop and Claude Code$\r$\n     so the MCP server is detected.$\r$\n  2. Double-click the Metis shortcut on your$\r$\n     Desktop to open the dashboard."
!define MUI_FINISHPAGE_RUN_TEXT "Launch Metis dashboard now"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchMetis

;--- Pages ---
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

;--------------------------------------------------------------
; Pre-flight: check WSL before showing installer pages
;--------------------------------------------------------------
Function .onInit
    nsExec::ExecToStack 'wsl.exe --status'
    Pop $0  ; exit code
    Pop $1  ; stdout

    ${If} $0 != 0
        MessageBox MB_OK|MB_ICONEXCLAMATION \
            "WSL (Windows Subsystem for Linux) is not installed.$\r$\n$\r$\nTo install it, open PowerShell as Administrator and run:$\r$\n$\r$\n    wsl --install$\r$\n$\r$\nRestart your computer, then run this installer again."
        Quit
    ${EndIf}
FunctionEnd

;--------------------------------------------------------------
; Main install section
;--------------------------------------------------------------
Section "Metis" SEC_METIS
    SetDetailsPrint both

    DetailPrint "Running Metis setup..."
    DetailPrint "(First install: 2-5 minutes. Updates are faster.)"
    DetailPrint ""

    ; Delegate all real work to install.ps1 (lives next to this .nsi file)
    nsExec::ExecToLog \
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -NonInteractive \
         -File "$EXEDIR\install.ps1"'
    Pop $0

    ${If} $0 != 0
        DetailPrint ""
        DetailPrint "[FAILED] See log above for details."
        MessageBox MB_OK|MB_ICONSTOP \
            "Installation failed.$\r$\nCheck the log window for details.$\r$\n$\r$\nCommon causes:$\r$\n  - WSL distro not yet installed (run: wsl --install)$\r$\n  - No internet connection during first install$\r$\n  - Python install blocked by corporate policy"
        Abort
    ${EndIf}

    DetailPrint ""
    DetailPrint "[OK] Metis installed successfully."
SectionEnd

;--------------------------------------------------------------
; Finish page: optionally launch the dashboard
;--------------------------------------------------------------
Function LaunchMetis
    ; launch-metis.bat is one level up from installer\
    ExecShell "" "$EXEDIR\..\launch-metis.bat"
FunctionEnd
