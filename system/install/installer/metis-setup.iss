; Metis Research Cortex — Inno Setup 6 Script
; Compile:       ISCC.exe metis-setup.iss  →  MetisSetup-1.0.exe
; GitHub Actions compiles automatically on every v* tag push.

#define MyAppName      "Metis Research Cortex"
#define MyAppVersion   "1.0"
#define MyAppPublisher "Metis Project"
#define MyAppURL       "https://github.com/SVerITG/Metis_PH"

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
MinVersion=10.0.17134

UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.WelcomeText=This will install Metis on your computer.%n%nMetis is an AI research companion that works alongside Claude. Everything runs on your computer — your research files never leave your machine.%n%nYou will need an Anthropic API key (free from console.anthropic.com).

; ── Component descriptions shown in wizard ───────────────────────────────────
[Types]
Name: "full";    Description: "Full — AI assistant + research dashboard (recommended)"
Name: "minimal"; Description: "AI only — AI assistant without dashboard (fastest, ~5 min)"
Name: "custom";  Description: "Custom installation"; Flags: iscustom

[Components]
Name: "core";      Description: "Metis core (34 agents, skills, config)";       Types: full minimal custom; Flags: fixed
Name: "dashboard"; Description: "Research dashboard (9-tab browser interface)"; Types: full custom

[Tasks]
Name: "desktopai";   Description: "Shortcut on desktop: Open Metis AI";    GroupDescription: "Shortcuts:"
Name: "desktopdash"; Description: "Shortcut on desktop: Open Dashboard";   GroupDescription: "Shortcuts:"; Components: dashboard
Name: "startmenu";   Description: "Create Start Menu folder";               GroupDescription: "Shortcuts:"

[Files]
; ── Agents and skills ────────────────────────────────────────────────────────
Source: "{#RepoRoot}\agents\*";  DestDir: "{app}\agents";  Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*-context.md"
Source: "{#RepoRoot}\.claude\*"; DestDir: "{app}\.claude"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Knowledge base ────────────────────────────────────────────────────────────
Source: "{#RepoRoot}\knowledge\course-template\*";  DestDir: "{app}\knowledge\course-template"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\knowledge\library\concepts\*"; DestDir: "{app}\knowledge\library\concepts"; Flags: ignoreversion recursesubdirs createallsubdirs
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

; ── Dashboard (optional component) ────────────────────────────────────────────
Source: "{#RepoRoot}\system\app-py\*"; DestDir: "{app}\system\app-py"; \
  Flags: ignoreversion recursesubdirs createallsubdirs; Components: dashboard; \
  Excludes: "*.pyc,__pycache__,.venv*,*.sqlite"

; ── Windows launcher and install scripts ──────────────────────────────────────
Source: "..\windows\install.ps1";        DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\bootstrap_python.ps1";       DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\download_vendor_python.ps1"; DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\windows\run-mcp.bat";        DestDir: "{app}\system\mcp-server";      Flags: ignoreversion
Source: "..\windows\run-dashboard.bat";  DestDir: "{app}\system\app-py";          Flags: ignoreversion; Components: dashboard
Source: "..\windows\run-tray.bat";       DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\tray_launcher.py";           DestDir: "{app}\system\install";         Flags: ignoreversion; Components: dashboard
Source: "..\dist\MetisTray.exe";         DestDir: "{app}\system\install\windows"; Flags: ignoreversion skipifsourcedoesntexist; Components: dashboard
Source: "..\vendor_download.py";         DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\config_merger.py";           DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\seed_ph_database.py";        DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\build_knowledge_db.py";      DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\process_wizard_answers.py";  DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\terminal_wizard.py";         DestDir: "{app}\system\install";         Flags: ignoreversion

; ── Bundled Python (offline fallback — built by download_vendor_python.ps1) ───
Source: "..\vendor\python-embed.zip"; DestDir: "{app}\vendor"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\vendor\get-pip.py";       DestDir: "{app}\vendor"; Flags: ignoreversion skipifsourcedoesntexist

; ── Docs ─────────────────────────────────────────────────────────────────────
Source: "{#RepoRoot}\..\CONTRIBUTING.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#RepoRoot}\..\README.md";       DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

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
; Start Menu
Name: "{group}\Metis — Open AI";    Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; Tasks: startmenu
Name: "{group}\Metis — Dashboard";  Filename: "wscript.exe"; \
  Parameters: """{app}\system\install\windows\launch-dashboard-silent.vbs"""; \
  IconFilename: "{app}\system\install\windows\metis.ico"; IconIndex: 0; \
  Tasks: startmenu; Components: dashboard
Name: "{group}\Uninstall Metis";    Filename: "{uninstallexe}"; Tasks: startmenu

; Desktop
Name: "{autodesktop}\Metis — Open AI"; Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; Tasks: desktopai
Name: "{autodesktop}\Metis";           Filename: "wscript.exe"; \
  Parameters: """{app}\system\install\windows\launch-dashboard-silent.vbs"""; \
  IconFilename: "{app}\system\install\windows\metis.ico"; IconIndex: 0; \
  Tasks: desktopdash; Components: dashboard

[Run]
; Step 0 — Python bootstrap (tries winget, python.org, then bundled embed)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\bootstrap_python.ps1"" -InstallDir ""{app}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Setting up Python…"

; Step 1a — Full install (with dashboard)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -SkipPython -SkipClaude -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Installing Metis (2–4 minutes)…"; \
  Components: dashboard

; Step 1b — Minimal install (AI only, no dashboard)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -Stage1Only -SkipPython -SkipClaude -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Configuring Metis AI assistant…"; \
  Components: not dashboard

; Step 2 — Demo workspace (only when user chose demo on the wizard page)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$py = $env:METIS_PYTHON; if (-not $py) { $py = 'python' }; & $py '{app}\system\install\seed_ph_database.py' --db '{app}\system\app\data\metis.sqlite' --quiet"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Loading demo workspace…"; \
  Check: ShouldSeedDemo

; Step 3 — Build PDF knowledge index (dashboard only, skips gracefully if library is empty)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$py = $env:METIS_PYTHON; if (-not $py) { $py = 'python' }; & $py '{app}\system\install\build_knowledge_db.py' --library-dir '{app}\knowledge\library' --db '{app}\system\app\data\metis.sqlite' --quiet"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Building knowledge database (5–15 min — Metis reads all included documents)…"; \
  Components: dashboard

; Step 4 — Process wizard answers through Claude API → writes metis-persona.md + project stubs
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$py = $env:METIS_PYTHON; if (-not $py) { $py = 'python' }; & $py '{app}\system\install\process_wizard_answers.py' --answers '{app}\system\wizard-answers.json' --metis-root '{app}' --quiet"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Personalising Metis to your research profile…"

; Final — offer to launch Claude Desktop (Metis starts automatically)
Filename: "{pf}\Anthropic\Claude\Claude.exe"; \
  Description: "Launch Claude Desktop — Metis starts automatically"; \
  Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\system\mcp-server\.venv-win"
Type: files;          Name: "{userappdata}\Claude\claude_desktop_config.json.metis-backup"

[Code]
var
  ApiKeyPage:    TInputQueryWizardPage;
  DemoPage:      TInputOptionWizardPage;
  AboutPage:     TInputQueryWizardPage;
  ResearchPage:  TInputQueryWizardPage;
  StylePage:     TInputOptionWizardPage;
  ProjectsPage:  TInputQueryWizardPage;

function ShouldSeedDemo: Boolean;
begin
  Result := (DemoPage.SelectedValueIndex = 0);
end;

function GetApiKey(Param: String): String;
begin
  Result := Trim(ApiKeyPage.Values[0]);
end;

procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption := CustomMessage('WelcomeText');

  { ── Demo workspace page ────────────────────────────────────────────────── }
  DemoPage := CreateInputOptionPage(
    wpSelectComponents,
    'Demo Workspace',
    'Would you like to start with a demo workspace?',
    'A demo workspace pre-loads a realistic example: projects, meetings, ' +
    'literature, and tasks — so you can explore every feature right away.' + #13#10 +
    'You can clear it and replace it with your own work at any time.',
    True, False);
  DemoPage.Add('Yes — start with demo content  (recommended for first-time users)');
  DemoPage.Add('No  — start with a blank workspace');
  DemoPage.SelectedValueIndex := 0;

  { ── API key page ────────────────────────────────────────────────────────── }
  ApiKeyPage := CreateInputQueryPage(
    DemoPage.ID,
    'Anthropic API Key',
    'Required to connect Metis to Claude AI.',
    'Your key is stored only on this computer and is never uploaded or shared.' + #13#10 +
    'Get a free key at: https://console.anthropic.com' + #13#10 + #13#10 +
    'The key looks like:  sk-ant-api03-…');
  ApiKeyPage.Add('Paste your API key here:', False);

  { ── About you page ─────────────────────────────────────────────────────── }
  AboutPage := CreateInputQueryPage(
    ApiKeyPage.ID,
    'About You',
    'Help Metis get to know you.',
    'Metis uses your answers to personalise how it communicates with you,' + #13#10 +
    'what it explains, and how it challenges your thinking.' + #13#10 + #13#10 +
    'This takes 2 minutes and makes a real difference.');
  AboutPage.Add('Your full name:', False);
  AboutPage.Add('Institution or organisation:', False);
  AboutPage.Add('Your role or title:', False);

  { ── Research page ──────────────────────────────────────────────────────── }
  ResearchPage := CreateInputQueryPage(
    AboutPage.ID,
    'Your Research',
    'What do you work on?',
    'Metis will calibrate its domain knowledge, literature alerts, and' + #13#10 +
    'terminology to your field.');
  ResearchPage.Add('Primary research field:', False);
  ResearchPage.Add('Key topics (comma-separated):', False);
  ResearchPage.Add('Tools and software you use daily:', False);

  { ── Working style page ─────────────────────────────────────────────────── }
  StylePage := CreateInputOptionPage(
    ResearchPage.ID,
    'Working Style',
    'How should Metis communicate with you?',
    'Choose the feedback approach that fits how you work.' + #13#10 +
    'You can change this any time.',
    True, False);
  StylePage.Add('Supportive — always encouraging, soften critique');
  StylePage.Add('Direct — honest and clear, skip the padding  (recommended)');
  StylePage.Add('Blunt — no hedging, challenge everything');
  StylePage.SelectedValueIndex := 1;

  { ── Projects page ──────────────────────────────────────────────────────── }
  ProjectsPage := CreateInputQueryPage(
    StylePage.ID,
    'Your Active Projects',
    'What are you currently working on?',
    'Metis will create a project card for each one so it can track your work.' + #13#10 +
    'Enter one project per line. You can add more later.');
  ProjectsPage.Add('Project 1:', False);
  ProjectsPage.Add('Project 2 (optional):', False);
  ProjectsPage.Add('Project 3 (optional):', False);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ApiKey: String;
begin
  Result := True;
  if CurPageID = ApiKeyPage.ID then
  begin
    ApiKey := Trim(ApiKeyPage.Values[0]);
    if Length(ApiKey) < 20 then
    begin
      MsgBox(
        'Please enter a valid Anthropic API key before continuing.' + #13#10 +
        'Get one free at https://console.anthropic.com',
        mbError, MB_OK);
      Result := False;
    end
    else if Copy(ApiKey, 1, 7) <> 'sk-ant-' then
    begin
      if MsgBox(
        'This key does not look like an Anthropic key (should start with sk-ant-).' + #13#10 +
        'Continue anyway?',
        mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end
  else if CurPageID = AboutPage.ID then
  begin
    if (Trim(AboutPage.Values[0]) = '') or (Trim(AboutPage.Values[2]) = '') then
    begin
      MsgBox('Please enter your name and role before continuing.', mbError, MB_OK);
      Result := False;
    end;
  end
  else if CurPageID = ResearchPage.ID then
  begin
    if Trim(ResearchPage.Values[0]) = '' then
    begin
      MsgBox('Please enter your primary research field before continuing.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ApiKey, EnvDir, EnvFile, EnvContent: String;
  StateFile, Profile, DashStr, DemoStr, StateContent: String;
  AnswersFile, AnswersContent, StyleStr: String;
  ProjectLines: String;
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

    { Build project list (non-empty entries only) }
    ProjectLines := '';
    for i := 0 to 2 do
    begin
      if Trim(ProjectsPage.Values[i]) <> '' then
      begin
        if ProjectLines <> '' then ProjectLines := ProjectLines + '\n';
        ProjectLines := ProjectLines + Trim(ProjectsPage.Values[i]);
      end;
    end;

    { Write .env }
    EnvDir  := ExpandConstant('{app}\system');
    ForceDirectories(EnvDir);
    EnvFile    := EnvDir + '\.env';
    EnvContent := 'ANTHROPIC_API_KEY=' + ApiKey + #13#10 +
                  'METIS_RC_ROOT=' + ExpandConstant('{app}') + #13#10;
    SaveStringToFile(EnvFile, EnvContent, False);

    { Write wizard answers as JSON for process_wizard_answers.py }
    AnswersFile := EnvDir + '\wizard-answers.json';
    AnswersContent :=
      '{' + #13#10 +
      '  "name": "' + Trim(AboutPage.Values[0]) + '",' + #13#10 +
      '  "institution": "' + Trim(AboutPage.Values[1]) + '",' + #13#10 +
      '  "role": "' + Trim(AboutPage.Values[2]) + '",' + #13#10 +
      '  "field": "' + Trim(ResearchPage.Values[0]) + '",' + #13#10 +
      '  "topics": "' + Trim(ResearchPage.Values[1]) + '",' + #13#10 +
      '  "tools": "' + Trim(ResearchPage.Values[2]) + '",' + #13#10 +
      '  "feedback_style": "' + StyleStr + '",' + #13#10 +
      '  "challenge_level": "balanced",' + #13#10 +
      '  "output_length": "concise",' + #13#10 +
      '  "projects": "' + ProjectLines + '",' + #13#10 +
      '  "language": "English"' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(AnswersFile, AnswersContent, False);

    { install-state.json }
    StateFile    := ExpandConstant('{app}\system\config\install-state.json');
    StateContent :=
      '{' + #13#10 +
      '  "profile": "' + Profile + '",' + #13#10 +
      '  "version": "' + '{#MyAppVersion}' + '",' + #13#10 +
      '  "demo_workspace": ' + DemoStr + ',' + #13#10 +
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

function InitializeSetup: Boolean;
begin
  Result := True;
  if not (GetWindowsVersion >= $0A000000) then
  begin
    MsgBox('Metis requires Windows 10 or later.', mbError, MB_OK);
    Result := False;
  end;
end;
