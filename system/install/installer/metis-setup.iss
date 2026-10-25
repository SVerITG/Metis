; Metis — Inno Setup 6 script
; Compile:  ISCC.exe metis-setup.iss                 -> dist\MetisSetup-<version>.exe
;           ISCC.exe /DMyAppVersion=1.2 metis-setup.iss
;
; ONE installer, not three. What gets installed is chosen in the wizard's
; [Types] page below (full / minimal / custom). CI used to compile this file
; three times with /DDefaultType=full|standard|minimal — a symbol this script
; never defined, so all three runs produced the SAME file under the SAME name,
; each overwriting the last, while the workflow then looked for three names
; that were never created. "standard" was not even one of the wizard's types.
;
; NOTE the #ifndef guards. A bare #define REPLACES a value passed with /D, so
; the version could not be set from the command line: every build was 1.0.

#ifndef MyAppName
  #define MyAppName    "Metis"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "1.0"
#endif

; The minimum Windows build, declared ONCE. It used to be stated three times
; with three different answers: this file's MinVersion said build 17134 (1803),
; a hand-rolled check below tested only "Windows 10 or later" and ignored the
; build entirely, and install.ps1 rejected anything under 17763 (1809). So a
; machine on 1803 was welcomed by the installer and then refused by the script
; it had just launched. 17763 is the real requirement; fail at the door.
#define MinWinBuild    "17763"   ; = Windows 10 version 1809
#define MyAppPublisher "Metis Project"
#define MyAppURL       "https://github.com/SVerITG/Metis"

; RepoRoot = 3 levels up: installer/ → install/ → system/ → repo root
#define RepoRoot       "..\..\.."

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Install to user's Documents — no admin required
DefaultDirName={userdocs}\Metis
DefaultGroupName={#MyAppName}
DisableDirPage=no
AllowNoIcons=yes

; No administrator rights needed for standard install
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Single output file — choices are made inside the wizard, not via separate builds
OutputDir=dist
OutputBaseFilename=MetisSetup-{#MyAppVersion}

Compression=lzma2/max
SolidCompression=yes
DiskSpanning=no
WizardStyle=modern
; Roomier wizard so page text + input fields are never clipped
WizardSizePercent=120
; Metis · Research Cortex branding — installer icon + welcome banner + header mark
SetupIconFile=..\windows\metis-brain.ico
WizardImageFile=..\windows\wizard-banner.bmp
WizardSmallImageFile=..\windows\wizard-small.bmp
MinVersion=10.0.{#MinWinBuild}
InfoBeforeFile=metis-info.txt
InfoAfterFile=metis-after.txt

UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.WelcomeText=Welcome to Metis — your AI research companion.%n%nMetis gives every Claude conversation a persistent memory of your domain, your papers, your projects, and your working history. The longer you use it, the better every response gets — because Metis knows you better, not because the AI changed.%n%nYou don't need to follow developments in AI. Metis does that for you.%n%nYour files and data stay on your computer. Only the text you choose to send for analysis goes to Claude (the Anthropic API); everything else stays local.%n%n────────────────────────────────────────────%n%nThis installer will:%n  1. Install the Metis AI core (MCP server + 33 specialist agents)%n  2. Optionally install the 9-tab research dashboard%n  3. Ask you a few questions to personalise Metis to your work%n%nInstallation takes 5–15 minutes depending on your connection.%nAn Anthropic API key is optional: Claude Desktop and Claude Code use your Claude subscription.

; ── Component descriptions shown in wizard ───────────────────────────────────
[Types]
Name: "full";    Description: "Full install — AI assistant + 9-tab research dashboard  (recommended)"
Name: "minimal"; Description: "AI only — just the AI assistant, no dashboard  (fastest, ~5 min)"
Name: "custom";  Description: "Custom — choose what to include"; Flags: iscustom

[Components]
Name: "core";      Description: "Metis AI assistant (33 specialist agents, MCP server, persistent memory)"; Types: full minimal custom; Flags: fixed
Name: "dashboard"; Description: "Research dashboard — 9 tabs: papers, meetings, ideas, projects, tasks, learning"; Types: full custom

[Tasks]
Name: "desktopai";   Description: "Shortcut on desktop: Open Metis AI";    GroupDescription: "Shortcuts:"
Name: "desktopdash"; Description: "Shortcut on desktop: Open Dashboard";   GroupDescription: "Shortcuts:"; Components: dashboard
Name: "startmenu";   Description: "Create Start Menu folder";               GroupDescription: "Shortcuts:"

[Files]
; ── Agents and skills ────────────────────────────────────────────────────────
Source: "{#RepoRoot}\agents\*";  DestDir: "{app}\agents";  Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*-context.md"
Source: "{#RepoRoot}\.claude\*"; DestDir: "{app}\.claude"; Flags: ignoreversion recursesubdirs createallsubdirs; \
  Excludes: "worktrees\*,projects\*,worktrees,projects"

; ── Knowledge base ────────────────────────────────────────────────────────────
Source: "{#RepoRoot}\knowledge\course-template\*";  DestDir: "{app}\knowledge\course-template"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\knowledge\library\concepts\*"; DestDir: "{app}\knowledge\library\concepts"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "{#RepoRoot}\knowledge\library\methods\*";  DestDir: "{app}\knowledge\library\methods";  Flags: ignoreversion recursesubdirs createallsubdirs

; ── System config (public files only — no personal data) ─────────────────────
Source: "{#RepoRoot}\system\config\constitution.md";     DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\red-lines.md";        DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\token-guardrails.md"; DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\first-run-wizard.md"; DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\tool-subsets.json";   DestDir: "{app}\system\config"; Flags: ignoreversion skipifsourcedoesntexist

; ── MCP server ────────────────────────────────────────────────────────────────
Source: "{#RepoRoot}\system\mcp-server\src\*";          DestDir: "{app}\system\mcp-server\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\system\mcp-server\pyproject.toml"; DestDir: "{app}\system\mcp-server";     Flags: ignoreversion
; The version lock install.ps1 installs under, and the database definition.
Source: "{#RepoRoot}\system\mcp-server\requirements.txt"; DestDir: "{app}\system\mcp-server"; Flags: ignoreversion
Source: "{#RepoRoot}\system\installer\schema.sql";        DestDir: "{app}\system\installer";  Flags: ignoreversion
Source: "{#RepoRoot}\system\installer\init_db.py";        DestDir: "{app}\system\installer";  Flags: ignoreversion

; ── Dashboard (optional component) ────────────────────────────────────────────
Source: "{#RepoRoot}\system\app-py\*"; DestDir: "{app}\system\app-py"; \
  Flags: ignoreversion recursesubdirs createallsubdirs; Components: dashboard; \
  Excludes: "*.pyc,__pycache__,.venv*,*.sqlite"

; ── Windows launcher and install scripts ──────────────────────────────────────
Source: "..\windows\install.ps1";               DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\windows\launch-dashboard-silent.vbs"; DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\windows\launch-dashboard.ps1";      DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\windows\metis.ico";                 DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\windows\metis-brain.ico";           DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\bootstrap_python.ps1";              DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\download_vendor_python.ps1";        DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\windows\run-mcp.bat";               DestDir: "{app}\system\mcp-server";      Flags: ignoreversion
Source: "..\windows\run-dashboard.bat";         DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\windows\run-tray.bat";              DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\windows\register-autostart.ps1";    DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\windows\autostart-dashboard.vbs";   DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\tray_launcher.py";           DestDir: "{app}\system\install";         Flags: ignoreversion; Components: dashboard
Source: "..\dist\MetisTray.exe";         DestDir: "{app}\system\install\windows"; Flags: ignoreversion skipifsourcedoesntexist; Components: dashboard
Source: "..\vendor_download.py";         DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\config_merger.py";           DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\register_desktop.py";        DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\metis_verify.py";            DestDir: "{app}\system\install";         Flags: ignoreversion
; Demo/seed content. Gitignored, so it is absent from a clean clone and the
; compile must not depend on it — without skipifsourcedoesntexist, ISCC
; fails outright and no installer can be built at all.
Source: "..\seed_mockup_demo.py";        DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\build_knowledge_db.py";      DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\process_wizard_answers.py";  DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\terminal_wizard.py";         DestDir: "{app}\system\install";         Flags: ignoreversion

; ── Bundled Python (offline fallback — built by download_vendor_python.ps1) ───
Source: "..\vendor\python-embed.zip"; DestDir: "{app}\vendor"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\vendor\get-pip.py";       DestDir: "{app}\vendor"; Flags: ignoreversion skipifsourcedoesntexist

; ── Docs ─────────────────────────────────────────────────────────────────────
Source: "{#RepoRoot}\CONTRIBUTING.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#RepoRoot}\README.md";       DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; "Configure & Fix Metis" help page — the door for metis-doctor / metis-customize
Source: "..\windows\configure-fix-metis.html"; DestDir: "{app}"; DestName: "Configure-and-Fix-Metis.html"; Flags: ignoreversion

[Dirs]
Name: "{app}\journal"
Name: "{app}\inbox"
Name: "{app}\inputs\meetings"
Name: "{app}\inputs\literature"
Name: "{app}\projects\active"
Name: "{app}\outputs\reviews"
Name: "{app}\archive"
Name: "{app}\system\app\data"
Name: "{app}\system\config"

[Icons]
; "Metis — Open AI" (Claude Desktop) is made by install.ps1, not here: Claude
; Desktop has no fixed path — the Microsoft Store edition has no .exe a shortcut
; can name — so only a script can find it. The Tasks are passed through to it.
; The dashboard opens through a VBScript, which starts it with no console window.
Name: "{group}\Metis — Dashboard";  Filename: "{sys}\wscript.exe"; \
  Parameters: """{app}\system\install\windows\launch-dashboard-silent.vbs"""; \
  IconFilename: "{app}\system\install\windows\metis-brain.ico"; IconIndex: 0; \
  Tasks: startmenu; Components: dashboard
; "Configure & Fix Metis" — the door to metis-doctor / metis-customize
Name: "{group}\Configure & Fix Metis"; Filename: "{app}\Configure-and-Fix-Metis.html"; \
  IconFilename: "{app}\system\install\windows\metis-brain.ico"; IconIndex: 0; Tasks: startmenu
Name: "{group}\Uninstall Metis";    Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{autodesktop}\Metis";        Filename: "{sys}\wscript.exe"; \
  Parameters: """{app}\system\install\windows\launch-dashboard-silent.vbs"""; \
  IconFilename: "{app}\system\install\windows\metis-brain.ico"; IconIndex: 0; \
  Tasks: desktopdash; Components: dashboard

[Run]
; install.ps1 does the work: Python (via uv), packages under the version lock,
; the database, Claude Desktop and Claude Code, shortcuts. It never prompts when
; called with -FromInstaller. Its log: {app}\system\install\install-log.txt
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -FromInstaller -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}""{code:ShortcutArgs}"; \
  Flags: waituntilterminated; \
  StatusMsg: "Installing Metis (5–10 minutes)…"; \
  Components: dashboard

Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -Stage1Only -FromInstaller -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}""{code:ShortcutArgs}"; \
  Flags: waituntilterminated; \
  StatusMsg: "Installing the Metis AI assistant (3–6 minutes)…"; \
  Components: not dashboard

; The steps below run in the environment install.ps1 just made — never a bare
; `python`, which on most computers is a different Python, or none — and write
; to the live database the server resolves, not the retired system\app\data.
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$env:METIS_RC_ROOT='{app}'; & '{app}\system\mcp-server\.venv-win\Scripts\python.exe' '{app}\system\install\seed_mockup_demo.py' --load --quiet *>> '{app}\system\install\install-log.txt'"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Loading demo workspace…"; \
  Check: ShouldSeedDemo

Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$env:METIS_RC_ROOT='{app}'; & '{app}\system\mcp-server\.venv-win\Scripts\python.exe' '{app}\system\install\build_knowledge_db.py' --library-dir '{app}\knowledge\library' --quiet *>> '{app}\system\install\install-log.txt'"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Building knowledge database (5–15 min — Metis reads all included documents)…"; \
  Components: dashboard

Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$env:METIS_RC_ROOT='{app}'; & '{app}\system\mcp-server\.venv-win\Scripts\python.exe' '{app}\system\install\process_wizard_answers.py' --answers '{app}\system\wizard-answers.json' --metis-root '{app}' --quiet *>> '{app}\system\install\install-log.txt'"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Personalising Metis to your research profile…"

; Opens Claude Desktop through the shortcut install.ps1 made, which works for
; both the classic and the Microsoft Store edition.
Filename: "{app}\Metis — Open AI.lnk"; \
  Description: "Open Claude Desktop — Metis is connected"; \
  Flags: shellexec postinstall nowait skipifsilent; \
  Check: FileExists(ExpandConstant('{app}\Metis — Open AI.lnk'))

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""Metis self-check"" /F"; \
  Flags: runhidden; RunOnceId: "RemoveMetisSelfCheck"
; Take Metis out of Claude Desktop's settings, leaving every other connector.
Filename: "{app}\system\mcp-server\.venv-win\Scripts\python.exe"; \
  Parameters: """{app}\system\install\register_desktop.py"" --remove"; \
  Flags: runhidden; RunOnceId: "RemoveMetisFromClaudeDesktop"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\system\mcp-server\.venv-win"
Type: files;          Name: "{app}\Metis — Open AI.lnk"
Type: files;          Name: "{autodesktop}\Metis — Open AI.lnk"
Type: files;          Name: "{userprograms}\Metis\Metis — Open AI.lnk"

[Code]
{ ── Page variables ──────────────────────────────────────────────────────── }
var
  ErrorCode:      Integer;
  DepPage:        TWizardPage;
  DepRowName:     array[0..4] of TNewStaticText;
  DepRowState:    array[0..4] of TNewStaticText;
  DepRowNote:     array[0..4] of TNewStaticText;
  DepSummary:     TNewStaticText;
  DepFixButton:   TNewButton;
  DepBlocked:     Boolean;
  McpConsentPage: TInputOptionWizardPage;
  DemoPage:       TInputOptionWizardPage;
  ApiKeyPage:     TInputQueryWizardPage;
  AboutPage:      TInputQueryWizardPage;
  ResearchPage:   TInputQueryWizardPage;
  StylePage:      TInputOptionWizardPage;
  ProjectsPage:   TWizardPage;
  PName:          array[0..2] of TNewEdit;
  PCat:           array[0..2] of TNewComboBox;
  PFolder:        array[0..2] of TNewEdit;
  PBrowse:        array[0..2] of TNewButton;

{ ── Pre-flight dependency check ──────────────────────────────────────────── }
{ Shown before anything is asked or installed. Three rules govern it:

  1. It BLOCKS only on what cannot be fixed from here. Something missing but
     installable is a warning with a button, not a wall.
  2. Every row says the CONSEQUENCE in words. "not found" tells a reader
     nothing; "Metis will run, but you will not get the chat interface" tells
     them whether to care.
  3. A check that cannot run reports that it could not run. It never reports
     "ready" by failing to look — the failure this whole project keeps hitting. }

const
  DEP_READY    = 0;   { present, nothing to do }
  DEP_FIXABLE  = 1;   { missing, and setup can install it }
  DEP_OPTIONAL = 2;   { missing, install continues, a feature is unavailable }
  DEP_BLOCKING = 3;   { missing, and setup cannot continue }
  DEP_UNKNOWN  = 4;   { the check itself could not run }

var
  DepState: array[0..4] of Integer;

function DepStateText(S: Integer): String;
begin
  case S of
    DEP_READY:    Result := 'ready';
    DEP_FIXABLE:  Result := 'will be installed';
    DEP_OPTIONAL: Result := 'not found';
    DEP_BLOCKING: Result := 'cannot continue';
  else
    Result := 'could not check';
  end;
end;

function FreeSpaceGB: Integer;
var
  Free, Total: Int64;
begin
  Result := -1;
  if GetSpaceOnDisk64(ExpandConstant('{sd}\'), Free, Total) then
    Result := Integer(Free div Int64(1073741824));
end;

function HaveClaudeDesktop: Boolean;
begin
  { Three install shapes. The Microsoft Store edition has no .exe we can see,
    but its package folder and its settings folder are fixed. }
  Result := FileExists(ExpandConstant('{localappdata}\AnthropicClaude\claude.exe'))
         or FileExists(ExpandConstant('{localappdata}\Programs\Claude\Claude.exe'))
         or FileExists(ExpandConstant('{commonpf}\Anthropic\Claude\Claude.exe'))
         or DirExists(ExpandConstant('{localappdata}\Packages\Claude_pzs8sxrjxfjjc'));
end;

{ install.ps1 makes the "Open AI" shortcuts (it is the only place that can find
  Claude Desktop); pass the shortcut choices through to it. }
function ShortcutArgs(Param: String): String;
begin
  Result := '';
  if WizardIsTaskSelected('desktopai') then Result := Result + ' -DesktopShortcut';
  if WizardIsTaskSelected('startmenu') then Result := Result + ' -StartMenuShortcut';
end;

function HavePython: Boolean;
var
  Dummy: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', Dummy)
         or RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', Dummy)
         or RegQueryStringValue(HKCU, 'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', Dummy)
         or RegQueryStringValue(HKCU, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', Dummy);
end;

procedure RefreshDependencies;
var
  i, ReadyCount, GB: Integer;
begin
  { 0 — Windows. MinVersion already refused anything older before this page
    could be reached, so this row exists to SHOW that it was checked. }
  DepRowName[0].Caption := 'Windows version';
  DepState[0] := DEP_READY;
  DepRowNote[0].Caption := 'Windows 10 build {#MinWinBuild} or newer is required.';

  { 1 — disk space. Blocking: nothing here can create room. }
  GB := FreeSpaceGB;
  DepRowName[1].Caption := 'Disk space';
  if GB < 0 then
  begin
    DepState[1] := DEP_UNKNOWN;
    DepRowNote[1].Caption := 'The free space on this drive could not be read. Setup will continue, but about 2 GB is needed.';
  end
  else if GB < 2 then
  begin
    DepState[1] := DEP_BLOCKING;
    DepRowNote[1].Caption := 'Only ' + IntToStr(GB) + ' GB free. Metis needs about 2 GB. Free some space and run setup again.';
  end
  else
  begin
    DepState[1] := DEP_READY;
    DepRowNote[1].Caption := IntToStr(GB) + ' GB free on this drive.';
  end;

  { 2 — Python. Fixable: setup bootstraps it. }
  DepRowName[2].Caption := 'Python';
  if HavePython then
  begin
    DepState[2] := DEP_READY;
    DepRowNote[2].Caption := 'Found. Setup still uses its own copy, so yours is not changed.';
  end
  else
  begin
    DepState[2] := DEP_FIXABLE;
    DepRowNote[2].Caption := 'Not needed in advance: setup fetches its own copy, separate from any other Python.';
  end;

  { 3 — the chat interface. Optional: Metis runs without it. }
  DepRowName[3].Caption := 'Claude Desktop';
  if HaveClaudeDesktop then
  begin
    DepState[3] := DEP_READY;
    DepRowNote[3].Caption := 'Found — Metis will connect itself to it.';
  end
  else
  begin
    DepState[3] := DEP_FIXABLE;
    DepRowNote[3].Caption := 'Not found. Setup will try to install it for you; if that fails, use the button below.';
  end;

  { 4 — where it will be installed. Informational, but people want to know. }
  DepRowName[4].Caption := 'Install location';
  DepState[4] := DEP_READY;
  // Not the app constant: this page comes before the folder is chosen, and
  // expanding it that early is a runtime error that stopped setup on its first
  // page. The folder box holds the default now and the choice later.
  DepRowNote[4].Caption := WizardForm.DirEdit.Text;

  ReadyCount := 0;
  DepBlocked := False;
  for i := 0 to 4 do
  begin
    DepRowState[i].Caption := DepStateText(DepState[i]);
    if DepState[i] = DEP_READY then ReadyCount := ReadyCount + 1;
    if DepState[i] = DEP_BLOCKING then DepBlocked := True;
  end;

  { The denominator is always stated. "5 checks" with no count is the shape
    that lets a check which never ran look like a check that passed. }
  DepSummary.Caption := IntToStr(ReadyCount) + ' of 5 checks ready';
  if DepBlocked then
    DepSummary.Caption := DepSummary.Caption + ' — setup cannot continue until the blocking item is resolved.';
end;

procedure DepFixClick(Sender: TObject);
begin
  { The only thing fixable from this page today is the chat interface, and the
    honest fix is to send them to the download rather than pretend to install
    it. Anything setup installs itself is already marked "will be installed". }
  if not HaveClaudeDesktop then
    ShellExec('open', 'https://claude.ai/download', '', '', SW_SHOW, ewNoWait, ErrorCode);
  RefreshDependencies;
end;

procedure CreateDependencyPage;
var
  i, Y: Integer;
begin
  DepPage := CreateCustomPage(wpWelcome,
    'Before we start',
    'Metis is checking this computer. Nothing has been installed or changed yet.');

  Y := 0;
  for i := 0 to 4 do
  begin
    DepRowName[i] := TNewStaticText.Create(DepPage);
    DepRowName[i].Parent := DepPage.Surface;
    DepRowName[i].Left := 0;
    DepRowName[i].Top := Y;
    DepRowName[i].AutoSize := True;
    DepRowName[i].Font.Style := [fsBold];

    DepRowState[i] := TNewStaticText.Create(DepPage);
    DepRowState[i].Parent := DepPage.Surface;
    DepRowState[i].Left := ScaleX(150);
    DepRowState[i].Top := Y;
    DepRowState[i].AutoSize := True;

    DepRowNote[i] := TNewStaticText.Create(DepPage);
    DepRowNote[i].Parent := DepPage.Surface;
    DepRowNote[i].Left := ScaleX(8);
    DepRowNote[i].Top := Y + ScaleY(14);
    DepRowNote[i].Width := DepPage.SurfaceWidth - ScaleX(8);
    DepRowNote[i].WordWrap := True;
    DepRowNote[i].AutoSize := True;

    Y := Y + ScaleY(46);
  end;

  DepSummary := TNewStaticText.Create(DepPage);
  DepSummary.Parent := DepPage.Surface;
  DepSummary.Left := 0;
  DepSummary.Top := Y + ScaleY(6);
  DepSummary.Width := DepPage.SurfaceWidth;
  DepSummary.WordWrap := True;
  DepSummary.AutoSize := True;
  DepSummary.Font.Style := [fsBold];

  DepFixButton := TNewButton.Create(DepPage);
  DepFixButton.Parent := DepPage.Surface;
  DepFixButton.Left := 0;
  DepFixButton.Top := Y + ScaleY(28);
  DepFixButton.Width := ScaleX(150);
  DepFixButton.Height := ScaleY(23);
  DepFixButton.Caption := 'Get Claude Desktop';
  DepFixButton.OnClick := @DepFixClick;
end;

{ ── Pascal helpers ──────────────────────────────────────────────────────── }
function ShouldSeedDemo: Boolean;
begin
  { Two conditions, not one. The user has to have asked for the demo AND the
    seed script has to actually be there: it is gitignored, so a clone does not
    carry it and [Files] installs it only if present. Without the second test
    the step launched python against a missing file, python exited, and the
    installer moved on reporting success — the demo silently absent. }
  Result := (DemoPage.SelectedValueIndex = 0)
            and FileExists(ExpandConstant('{app}\system\install\seed_mockup_demo.py'));
end;

function GetApiKey(Param: String): String;
begin
  Result := Trim(ApiKeyPage.Values[0]);
end;

{ Escape a string for JSON — replace backslashes and double-quotes }
function JsonEsc(S: String): String;
var
  i: Integer;
  C: Char;
  R: String;
begin
  R := '';
  for i := 1 to Length(S) do
  begin
    C := S[i];
    if C = '\' then R := R + '\\'
    else if C = '"' then R := R + '\"'
    else R := R + C;
  end;
  Result := R;
end;

{ Browse-for-folder handler shared by the three project folder fields.
  The button's Tag holds the project index (0..2). }
procedure BrowseProjectFolder(Sender: TObject);
var
  Dir: String;
  idx: Integer;
begin
  idx := TNewButton(Sender).Tag;
  Dir := PFolder[idx].Text;
  if BrowseForFolder('Select the folder for this project', Dir, False) then
    PFolder[idx].Text := Dir;
end;

{ ── Wizard initialisation ───────────────────────────────────────────────── }
procedure InitializeWizard;
var
  i: Integer;
  Lbl: TNewStaticText;
begin
  WizardForm.WelcomeLabel2.Caption := CustomMessage('WelcomeText');

  { Pre-flight first: nothing is asked until the machine has been looked at. }
  CreateDependencyPage;

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 1 — MCP SERVER AUTHORISATION
    Shown right after the component selection page.
    Explains what the MCP server is and asks for explicit consent.
    ═══════════════════════════════════════════════════════════════════════ }
  McpConsentPage := CreateInputOptionPage(
    wpSelectComponents,
    'Authorise Background Component',
    'The MCP server — what it does and what you are authorising.',
    'Metis installs a small background program — the MCP server (Model Context' + #13#10 +
    'Protocol, an open Anthropic standard). It sits between Claude and your' + #13#10 +
    'research files, fetching the right context when you ask a question.' + #13#10 +
    '' + #13#10 +
    'It reads/writes only inside your Metis folder, keeps all data local' + #13#10 +
    '(nothing is sent anywhere), and runs only while Claude is open.' + #13#10 +
    'Remove it any time via Windows Settings -> Apps -> Metis.',
    False, False);
  McpConsentPage.Add(
    'I understand what the MCP server does and authorise its installation');
  McpConsentPage.CheckListBox.Checked[0] := True;

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 2 — DEMO WORKSPACE
    ═══════════════════════════════════════════════════════════════════════ }
  DemoPage := CreateInputOptionPage(
    McpConsentPage.ID,
    'Demo Workspace',
    'Start with example content so you can explore every feature right away?',
    'A demo workspace pre-loads a realistic scenario — example projects, meeting' + #13#10 +
    'notes, a small literature library, and some open tasks — so you can explore' + #13#10 +
    'every dashboard tab right away. Clear it and add your own work any time' + #13#10 +
    '(Metis dashboard -> Settings -> Clear demo content).',
    True, False);
  DemoPage.Add('Yes — load demo content  (recommended for first-time users)');
  DemoPage.Add('No  — start with a blank workspace');
  DemoPage.SelectedValueIndex := 0;

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 3 — ANTHROPIC API KEY
    ═══════════════════════════════════════════════════════════════════════ }
  ApiKeyPage := CreateInputQueryPage(
    DemoPage.ID,
    'Anthropic API Key (optional)',
    'Leave this empty if you use Claude Desktop or Claude Code — they do not need it.',
    'Metis works through your Claude subscription in Claude Desktop and Claude Code.' + #13#10 +
    'An API key only powers background features, such as the automatic morning brief.' + #13#10 +
    '' + #13#10 +
    'API keys are paid separately:  https://console.anthropic.com  ->  API Keys' + #13#10 +
    'It is stored on this PC in a local .env file (it looks like sk-ant-api03-…);' + #13#10 +
    'what Metis sends to Claude for those features goes to the Anthropic API.');
  ApiKeyPage.Add('Paste your Anthropic API key here:', False);

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 4 — ABOUT YOU
    ═══════════════════════════════════════════════════════════════════════ }
  AboutPage := CreateInputQueryPage(
    ApiKeyPage.ID,
    'About You',
    'Help Metis get to know you — this takes about 1 minute.',
    'Metis uses this to address you by name, calibrate how it communicates,' + #13#10 +
    'and route questions to the right agent. It stays on this computer.' + #13#10 +
    'Update any time with  /metis_config  in Claude.');
  AboutPage.Add('Your full name:', False);
  AboutPage.Add('Institution or organisation (optional):', False);
  AboutPage.Add('Your role or title (e.g. PhD researcher, epidemiologist, professor):', False);

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 5 — YOUR RESEARCH
    ═══════════════════════════════════════════════════════════════════════ }
  { Three boxes, not one, because they are weighted differently downstream and
    a single list cannot express the difference. A subject you work IN counts
    almost as much as an active project; a method you occasionally apply counts
    noticeably less; and what you want WATCHED in the news is a different
    question again — you follow news about things you do not research yourself.
    Collected flat, all of it collapsed to one middle weight, and the engine
    could not tell a standing subject from a passing interest. }
  ResearchPage := CreateInputQueryPage(
    AboutPage.ID,
    'Your Research Domain',
    'Three different questions — they are used differently, so keep them apart.',
    'FIELD is what you work in; it ranks almost as high as an active project.' + #13#10 +
    'METHODS are techniques you apply sometimes; they surface occasionally.' + #13#10 +
    'NEWS is what you want watched in the world — often broader than your own' + #13#10 +
    'research. Separate each with commas. All of it is editable later.');
  ResearchPage.Add('Your field — subjects you work IN (e.g. epidemiology, surveillance):', False);
  ResearchPage.Add('Methods you use — techniques, not subjects (e.g. spatial analysis, mixed models):', False);
  ResearchPage.Add('Watch in the news — topics to follow, even outside your own work:', False);
  ResearchPage.Add('Tools and software you use regularly (optional):', False);

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 6 — WORKING STYLE
    ═══════════════════════════════════════════════════════════════════════ }
  StylePage := CreateInputOptionPage(
    ResearchPage.ID,
    'Communication Style',
    'How should Metis give you feedback?',
    'Metis reviews your methods, critiques writing, and challenges your thinking.' + #13#10 +
    'Choose the feedback approach that suits you (affects tone, not knowledge).' + #13#10 +
    'Change any time from the Metis tab -> Appearance.',
    True, False);
  StylePage.Add('Supportive — always encouraging; critiques are wrapped in positive framing');
  StylePage.Add('Direct — honest and clear; calls out problems without softening  (recommended)');
  StylePage.Add('Blunt — no hedging; challenges assumptions; short and straight');
  StylePage.SelectedValueIndex := 1;

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 7 — ACTIVE PROJECTS (names + categories)
    ═══════════════════════════════════════════════════════════════════════ }
  ProjectsPage := CreateCustomPage(
    StylePage.ID,
    'Your Active Projects',
    'What are you working on? Every field here is optional — add as much or as ' +
    'little as you like, and add more later from the dashboard.');

  { Plain-language explainer (the same calm guidance the dashboard gives) }
  Lbl := TNewStaticText.Create(ProjectsPage);
  Lbl.Parent := ProjectsPage.Surface;
  Lbl.Left := 0;
  Lbl.Top := 0;
  Lbl.Width := ProjectsPage.SurfaceWidth;
  Lbl.WordWrap := True;
  Lbl.AutoSize := True;
  Lbl.Caption :=
    'A project is any body of work you want Metis to track — an article, grant, course, ' +
    'dataset, or tool. The folder is optional: pick one and Metis reads the work already ' +
    'in it (files, notes, git history); leave it blank to track the project by name only.';

  for i := 0 to 2 do
  begin
    { Bold row header }
    Lbl := TNewStaticText.Create(ProjectsPage);
    Lbl.Parent := ProjectsPage.Surface;
    Lbl.Top := ScaleY(48) + i * ScaleY(74);
    Lbl.Left := 0;
    Lbl.AutoSize := True;
    Lbl.Font.Style := [fsBold];
    Lbl.Caption := 'Project ' + IntToStr(i + 1) + '  (optional)';

    { Name (left) }
    PName[i] := TNewEdit.Create(ProjectsPage);
    PName[i].Parent := ProjectsPage.Surface;
    PName[i].Top := Lbl.Top + ScaleY(16);
    PName[i].Left := 0;
    PName[i].Width := ScaleX(240);
    PName[i].Hint := 'Project name';
    PName[i].ShowHint := True;

    { Category dropdown (right of name) — editable: pick or type your own }
    PCat[i] := TNewComboBox.Create(ProjectsPage);
    PCat[i].Parent := ProjectsPage.Surface;
    PCat[i].Top := PName[i].Top;
    PCat[i].Left := ScaleX(248);
    PCat[i].Width := ProjectsPage.SurfaceWidth - ScaleX(248);
    PCat[i].Style := csDropDown;
    PCat[i].Items.Add('Article');
    PCat[i].Items.Add('Grant');
    PCat[i].Items.Add('Teaching');
    PCat[i].Items.Add('Software');
    PCat[i].Items.Add('Review');
    PCat[i].Items.Add('Dataset');
    PCat[i].Items.Add('Course');
    PCat[i].Items.Add('Thesis');

    { Folder (full width, with Browse button) — optional }
    PFolder[i] := TNewEdit.Create(ProjectsPage);
    PFolder[i].Parent := ProjectsPage.Surface;
    PFolder[i].Top := PName[i].Top + ScaleY(26);
    PFolder[i].Left := 0;
    PFolder[i].Width := ProjectsPage.SurfaceWidth - ScaleX(96);
    PFolder[i].Hint := 'Local folder (optional) — leave blank to skip';
    PFolder[i].ShowHint := True;

    PBrowse[i] := TNewButton.Create(ProjectsPage);
    PBrowse[i].Parent := ProjectsPage.Surface;
    PBrowse[i].Top := PFolder[i].Top - ScaleY(1);
    PBrowse[i].Left := ProjectsPage.SurfaceWidth - ScaleX(90);
    PBrowse[i].Width := ScaleX(90);
    PBrowse[i].Height := ScaleY(23);
    PBrowse[i].Caption := 'Browse...';
    PBrowse[i].Tag := i;
    PBrowse[i].OnClick := @BrowseProjectFolder;
  end;
end;

{ ── Validation on Next ──────────────────────────────────────────────────── }
function IsClaudeRunning: Boolean;
var
  Locator, Service, Procs: Variant;
begin
  Result := False;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('.', 'root\CIMV2');
    Procs := Service.ExecQuery('SELECT ProcessId FROM Win32_Process WHERE Name = ''claude.exe''');
    Result := Procs.Count > 0;
  except
    Result := False;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
var
  ResultCode: Integer;
  Link: String;
begin
  if (DepPage <> nil) and (CurPageID = DepPage.ID) then
    RefreshDependencies;

  // Claude Desktop reads its connectors only when it starts. If it was open
  // during setup, Metis stays invisible until it is quit completely, which
  // nobody would guess, so offer to do it.
  if (CurPageID = wpFinished) and (not WizardSilent) and IsClaudeRunning then
  begin
    // One line on purpose: a line that begins with # is read as a preprocessor directive.
    if MsgBox('Claude Desktop is open. It has to restart once to connect to Metis.' + #13#10 + #13#10 + 'Restart Claude Desktop now?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM claude.exe /F', '', SW_HIDE,
           ewWaitUntilTerminated, ResultCode);
      Sleep(1500);
      Link := ExpandConstant('{app}\Metis — Open AI.lnk');
      if FileExists(Link) then
        ShellExec('open', Link, '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
    end;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ApiKey: String;
begin
  Result := True;
  { A silent install (/VERYSILENT, used by IT departments and by the release
    build's own install test) never shows these pages. A check that refuses an
    empty answer would refuse it for ever, behind a suppressed message box: setup
    hung indefinitely. Silent means defaults, so the checks do not apply. }
  if WizardSilent then Exit;

  if (DepPage <> nil) and (CurPageID = DepPage.ID) then
  begin
    { Only a blocking check stops us. Missing-but-installable and
      missing-but-optional both let setup continue, by design. }
    if DepBlocked then
    begin
      MsgBox('Setup cannot continue yet.' + #13#10 + #13#10 +
             'One of the checks above has to be resolved first — it is not '
             + 'something setup can fix for you. Resolve it and run setup again.',
             mbError, MB_OK);
      Result := False;
    end;
  end

  else if CurPageID = McpConsentPage.ID then
  begin
    if not McpConsentPage.CheckListBox.Checked[0] then
    begin
      MsgBox(
        'Please tick the authorisation checkbox to continue.' + #13#10 +
        'You can remove the MCP server at any time from Windows Settings → Apps.',
        mbInformation, MB_OK);
      Result := False;
    end;
  end

  else if CurPageID = ApiKeyPage.ID then
  begin
    ApiKey := Trim(ApiKeyPage.Values[0]);
    { Skippable on purpose. Someone evaluating Metis should not be stopped at
      the door because they have not signed up yet; the finish page tells them
      what is still missing and where to add it. An empty key is a choice. }
    if ApiKey = '' then
      Result := True
    else if Length(ApiKey) < 20 then
    begin
      if MsgBox(
        'That key looks too short to be valid.' + #13#10 + #13#10 +
        'Leave it blank to skip for now — you can add it later from the Metis '
        + 'tab — or paste the full key.' + #13#10 + #13#10 + 'Continue anyway?',
        mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
    end
    else if Copy(ApiKey, 1, 7) <> 'sk-ant-' then
    begin
      if MsgBox(
        'This key does not look like an Anthropic key.' + #13#10 +
        'Valid Anthropic keys start with  sk-ant-' + #13#10 + #13#10 +
        'Continue anyway?',
        mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end

  else if CurPageID = AboutPage.ID then
  begin
    if Trim(AboutPage.Values[0]) = '' then
    begin
      MsgBox('Metis personalises everything to you — please enter your name to continue.'
        + #13#10 + 'You can change it any time later with  /metis_config.', mbInformation, MB_OK);
      Result := False;
    end
    else if Trim(AboutPage.Values[2]) = '' then
    begin
      MsgBox('Please add your role or title so Metis can pitch its language right'
        + #13#10 + '(e.g. PhD researcher, epidemiologist, professor).', mbInformation, MB_OK);
      Result := False;
    end;
  end

  else if CurPageID = ResearchPage.ID then
  begin
    if Trim(ResearchPage.Values[0]) = '' then
    begin
      MsgBox(
        'Please enter your primary research field before continuing.' + #13#10 +
        'Example: Epidemiology, Public Health, Global Health, Biostatistics',
        mbError, MB_OK);
      Result := False;
    end;
  end;
end;

{ ── Write config files after install ────────────────────────────────────── }
procedure CurStepChanged(CurStep: TSetupStep);
var
  ApiKey, EnvDir, EnvFile, EnvContent: String;
  StateFile, Profile, DashStr, DemoStr, StateContent: String;
  AnswersFile, AnswersContent, StyleStr: String;
  ProjectLines: String;
  ProjName, ProjCat, ProjFolder: String;
  HasDash: Boolean;
  i: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ApiKey  := Trim(ApiKeyPage.Values[0]);
    HasDash := WizardIsComponentSelected('dashboard');
    if HasDash then begin Profile := 'full'; DashStr := 'true'; end
    else begin Profile := 'minimal'; DashStr := 'false'; end;
    if DemoPage.SelectedValueIndex = 0 then DemoStr := 'true'
    else DemoStr := 'false';

    case StylePage.SelectedValueIndex of
      0: StyleStr := 'gentle';
      2: StyleStr := 'blunt';
    else
      StyleStr := 'direct';
    end;

    { Build project list as JSON array from the custom Projects page —
      name + category (dropdown or typed) + optional folder per project. }
    ProjectLines := '[';
    for i := 0 to 2 do
    begin
      if Trim(PName[i].Text) <> '' then
      begin
        ProjName   := Trim(PName[i].Text);
        ProjCat    := Trim(PCat[i].Text);
        ProjFolder := Trim(PFolder[i].Text);

        if ProjectLines <> '[' then ProjectLines := ProjectLines + ',' + #13#10;
        ProjectLines := ProjectLines +
          '  {"name":"' + JsonEsc(ProjName) + '"' +
          ',"category":"' + JsonEsc(ProjCat) + '"' +
          ',"folder":"' + JsonEsc(ProjFolder) + '"}';
      end;
    end;
    ProjectLines := ProjectLines + #13#10 + ']';

    { Write system/.env }
    EnvDir  := ExpandConstant('{app}\system');
    ForceDirectories(EnvDir);
    EnvFile    := EnvDir + '\.env';
    { Re-running setup to update Metis must not erase a key entered last time:
      install.ps1 merges the values in and keeps every other line. }
    if not FileExists(EnvFile) then
    begin
      EnvContent := 'METIS_RC_ROOT=' + ExpandConstant('{app}') + #13#10;
      SaveStringToFile(EnvFile, EnvContent, False);
    end;

    { Write system/wizard-answers.json for process_wizard_answers.py }
    AnswersFile    := EnvDir + '\wizard-answers.json';
    AnswersContent :=
      '{' + #13#10 +
      '  "name": "'        + JsonEsc(Trim(AboutPage.Values[0]))    + '",' + #13#10 +
      '  "institution": "' + JsonEsc(Trim(AboutPage.Values[1]))    + '",' + #13#10 +
      '  "role": "'        + JsonEsc(Trim(AboutPage.Values[2]))    + '",' + #13#10 +
      { Named by BAND, not lumped as "topics". These map straight onto
        user_topics.band downstream: field=0.95, method=0.72, and news terms
        drive the brief rather than relevance scoring. }
      '  "field": "'       + JsonEsc(Trim(ResearchPage.Values[0])) + '",' + #13#10 +
      '  "methods": "'     + JsonEsc(Trim(ResearchPage.Values[1])) + '",' + #13#10 +
      '  "news_terms": "'  + JsonEsc(Trim(ResearchPage.Values[2])) + '",' + #13#10 +
      '  "tools": "'       + JsonEsc(Trim(ResearchPage.Values[3])) + '",' + #13#10 +
      '  "feedback_style": "' + StyleStr + '",' + #13#10 +
      '  "challenge_level": "balanced",' + #13#10 +
      '  "output_length": "concise",' + #13#10 +
      '  "projects": ' + ProjectLines + ',' + #13#10 +
      '  "language": "English"' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(AnswersFile, AnswersContent, False);

    { Write system/config/install-state.json }
    StateFile    := ExpandConstant('{app}\system\config\install-state.json');
    StateContent :=
      '{' + #13#10 +
      '  "profile": "'  + Profile + '",' + #13#10 +
      '  "version": "'  + '{#MyAppVersion}' + '",' + #13#10 +
      '  "demo_workspace": ' + DemoStr + ',' + #13#10 +
      '  "mcp_consent": true,' + #13#10 +
      '  "installed_at": "' + GetDateTimeString('yyyy/mm/dd hh:nn:ss', '-', ':') + '",' + #13#10 +
      '  "components": {' + #13#10 +
      '    "mcp_server": true,' + #13#10 +
      '    "dashboard": ' + DashStr + ',' + #13#10 +
      '    "docker": false' + #13#10 +
      '  }' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(StateFile, StateContent, False);
  end;
end;

{ ── Windows version guard ────────────────────────────────────────────────── }
function InitializeSetup: Boolean;
begin
  Result := True;
  { The Windows version gate is MinVersion in [Setup] — Inno enforces it before
    this runs and reports it properly. A second hand-rolled check here tested
    only the major version, so it passed builds MinVersion rejects. Removed. }
end;
