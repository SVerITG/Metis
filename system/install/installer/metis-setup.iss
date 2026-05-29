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
english.WelcomeText=Welcome to Metis — your AI research companion.%n%nMetis works alongside Claude to give every AI conversation a persistent memory of your domain, your papers, your projects, and your working history. The longer you use it, the better every response gets.%n%nEverything runs on your computer. Your research files never leave your machine.%n%n────────────────────────────────────────────%n%nWhat this installer does:%n  1. Installs the Metis MCP server — a small background%n     program that connects Claude to your research world%n  2. (Optional) Installs the 9-tab research dashboard%n  3. Asks you a few questions to personalise Metis to you%n%nYou will need a free Anthropic API key from console.anthropic.com%n(takes 2 minutes — instructions on the next page).

; ── Component descriptions shown in wizard ───────────────────────────────────
[Types]
Name: "full";    Description: "Full install — AI assistant + 9-tab research dashboard  (recommended)"
Name: "minimal"; Description: "AI only — just the AI assistant, no dashboard  (fastest, ~5 min)"
Name: "custom";  Description: "Custom — choose what to include"; Flags: iscustom

[Components]
Name: "core";      Description: "Metis AI assistant (34 specialist agents, MCP server, persistent memory)"; Types: full minimal custom; Flags: fixed
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
Source: "..\windows\install.ps1";               DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\windows\launch-dashboard-silent.vbs"; DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\windows\metis.ico";                 DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\windows\metis-brain.ico";           DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\bootstrap_python.ps1";              DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\download_vendor_python.ps1";        DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\windows\run-mcp.bat";               DestDir: "{app}\system\mcp-server";      Flags: ignoreversion
Source: "..\windows\run-dashboard.bat";         DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\windows\run-tray.bat";              DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
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

; Desktop — Claude shortcut only created if Claude Desktop is installed
Name: "{autodesktop}\Metis — Open AI"; Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; Tasks: desktopai; \
  Check: FileExists(ExpandConstant('{commonpf}\Anthropic\Claude\Claude.exe'))
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
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$py = $env:METIS_PYTHON; if (-not $py) {{ $py = 'python' }}; & $py '{app}\system\install\seed_ph_database.py' --db '{app}\system\app\data\metis.sqlite' --quiet"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Loading demo workspace…"; \
  Check: ShouldSeedDemo

; Step 3 — Build PDF knowledge index (dashboard only, skips gracefully if library is empty)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$py = $env:METIS_PYTHON; if (-not $py) {{ $py = 'python' }}; & $py '{app}\system\install\build_knowledge_db.py' --library-dir '{app}\knowledge\library' --db '{app}\system\app\data\metis.sqlite' --quiet"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Building knowledge database (5–15 min — Metis reads all included documents)…"; \
  Components: dashboard

; Step 4 — Process wizard answers through Claude API → writes metis-persona.md + project stubs
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$py = $env:METIS_PYTHON; if (-not $py) {{ $py = 'python' }}; & $py '{app}\system\install\process_wizard_answers.py' --answers '{app}\system\wizard-answers.json' --metis-root '{app}' --quiet"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Personalising Metis to your research profile…"

; Final — offer to launch Claude Desktop only if it is actually installed
Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; \
  Description: "Launch Claude Desktop — Metis starts automatically"; \
  Flags: postinstall nowait skipifsilent; \
  Check: FileExists(ExpandConstant('{commonpf}\Anthropic\Claude\Claude.exe'))

[UninstallDelete]
Type: filesandordirs; Name: "{app}\system\mcp-server\.venv-win"
Type: files;          Name: "{userappdata}\Claude\claude_desktop_config.json.metis-backup"

[Code]
var
  ApiKeyPage:      TInputQueryWizardPage;
  DemoPage:        TInputOptionWizardPage;
  AboutPage:       TInputQueryWizardPage;
  ResearchPage:    TInputQueryWizardPage;
  StylePage:       TInputOptionWizardPage;
  ProjectsPage:    TInputQueryWizardPage;
  WhatMetisPage:   TOutputMsgMemoWizardPage;
  DataPrivacyPage: TOutputMsgMemoWizardPage;

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

  { ── What Metis is doing — educational page shown before install questions ── }
  WhatMetisPage := CreateOutputMsgMemoWizardPage(
    wpSelectComponents,
    'How Metis Works — What to Expect',
    'A quick overview before we ask you a few questions.',
    '',
    'WHAT IS AN MCP SERVER?' + #13#10 +
    'MCP (Model Context Protocol) is an open standard from Anthropic.' + #13#10 +
    'Metis uses it to give Claude a persistent connection to your research' + #13#10 +
    'world — your papers, your projects, your notes, your meeting history.' + #13#10 +
    'The MCP server is a small background process that runs silently.' + #13#10 +
    'You will never interact with it directly — it just works.' + #13#10 + #13#10 +
    '────────────────────────────────────────────────────────────' + #13#10 + #13#10 +
    'HOW YOU WILL KNOW METIS IS WORKING' + #13#10 +
    'Once installed, open Claude Desktop or Claude Code. Metis will:' + #13#10 +
    '  • Remember what you were working on in your last session' + #13#10 +
    '  • Know your research domain and your terminology' + #13#10 +
    '  • Route your questions to the right specialist (Epidemiologist,' + #13#10 +
    '    Writing Partner, Librarian, Methods Coach, and 30+ others)' + #13#10 +
    '  • Cross-reference your ideas with your literature automatically' + #13#10 +
    '  • Build a morning brief of new papers and field news overnight' + #13#10 + #13#10 +
    '────────────────────────────────────────────────────────────' + #13#10 + #13#10 +
    'WHAT THE DASHBOARD ADDS (if you chose Full install)' + #13#10 +
    'The research dashboard opens in your browser at http://localhost:8080.' + #13#10 +
    'It is your research hub — 9 tabs covering papers, meetings, ideas,' + #13#10 +
    'projects, tasks, learning, and more. It reads the same database as' + #13#10 +
    'the MCP server, so everything is always in sync.' + #13#10 + #13#10 +
    '────────────────────────────────────────────────────────────' + #13#10 + #13#10 +
    'WHAT HAPPENS DURING INSTALL' + #13#10 +
    '  Step 1  Sets up Python (required to run the MCP server)' + #13#10 +
    '  Step 2  Installs Metis packages (may take 5-15 minutes)' + #13#10 +
    '  Step 3  Loads demo data (if you chose the demo option)' + #13#10 +
    '  Step 4  Builds your knowledge index from included documents' + #13#10 +
    '  Step 5  Personalises Metis to your research profile' + #13#10 +
    '  Step 6  Registers Metis with Claude Desktop and Claude Code',
    0);

  { ── Demo workspace page ────────────────────────────────────────────────── }
  DemoPage := CreateInputOptionPage(
    WhatMetisPage.ID,
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
    'Connect Metis to Claude AI.',
    'How to get your free API key:' + #13#10 +
    '  1. Open: https://console.anthropic.com' + #13#10 +
    '  2. Sign up or log in (free account)' + #13#10 +
    '  3. Click "API Keys" → "Create Key"' + #13#10 +
    '  4. Copy the key and paste it below' + #13#10 + #13#10 +
    'Your key stays on this computer — it is never uploaded or shared.' + #13#10 +
    'The key looks like:  sk-ant-api03-…');
  ApiKeyPage.Add('Paste your Anthropic API key here:', False);

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

  { ── Data privacy page ──────────────────────────────────────────────────── }
  DataPrivacyPage := CreateOutputMsgMemoWizardPage(
    StylePage.ID,
    'Your Data is Protected — Here is How',
    'Before you add your projects, understand exactly what Metis touches.',
    '',
    'WHAT STAYS ON YOUR MACHINE — ALWAYS' + #13#10 +
    '  ✓  Your PDF library and all indexed documents' + #13#10 +
    '  ✓  Your meeting notes and transcripts' + #13#10 +
    '  ✓  Your ideas, journal entries, and task lists' + #13#10 +
    '  ✓  Your project files and folder contents' + #13#10 +
    '  ✓  Your API key and credentials (stored in a local .env file)' + #13#10 +
    '  ✓  All voice recordings' + #13#10 + #13#10 +
    '────────────────────────────────────────────────────────────' + #13#10 + #13#10 +
    'WHAT LEAVES YOUR MACHINE (and when)' + #13#10 +
    '  → Anthropic Claude API: text you send for analysis' + #13#10 +
    '    (same as typing in Claude Desktop directly)' + #13#10 +
    '  → PubMed / OpenAlex: your configured research search terms' + #13#10 +
    '    (sent once per day for the morning brief — optional)' + #13#10 +
    '  → Zotero: library metadata if you enable sync (optional)' + #13#10 + #13#10 +
    '────────────────────────────────────────────────────────────' + #13#10 + #13#10 +
    'WHEN PROJECT FOLDERS ARE SCANNED' + #13#10 +
    'If you give Metis a folder path for a project, it can scan it.' + #13#10 +
    'You choose what it reads:' + #13#10 +
    '  • "File names only" — sees file and folder names, nothing else' + #13#10 +
    '  • "Read notes" — also reads README.md and PLANNING.md' + #13#10 +
    '  • "I will describe it" — no scan at all, you type the description' + #13#10 + #13#10 +
    'Metis NEVER reads patient data files — they are detected and blocked.' + #13#10 +
    'Metis NEVER reads files outside your configured project folders.' + #13#10 + #13#10 +
    '────────────────────────────────────────────────────────────' + #13#10 + #13#10 +
    'YOUR CLAUDE.md FILE' + #13#10 +
    'For each project folder you provide, Metis writes a CLAUDE.md file.' + #13#10 +
    'This is a plain text file that tells Claude what the project is about.' + #13#10 +
    'Claude Desktop and Claude Code read it automatically when you open' + #13#10 +
    'the folder. You can edit or delete it at any time — it is yours.',
    0);

  { ── Projects page ──────────────────────────────────────────────────────── }
  ProjectsPage := CreateInputQueryPage(
    DataPrivacyPage.ID,
    'Your Active Projects',
    'Tell Metis what you are currently working on.',
    'Enter up to 3 projects below. You can add more after install' + #13#10 +
    'from the Metis dashboard (http://localhost:8080/setup).' + #13#10 + #13#10 +
    'Format options (all parts are optional — name alone is fine):' + #13#10 +
    '  Just a name:       HAT Surveillance Study' + #13#10 +
    '  With category:     HAT Surveillance Study | Article' + #13#10 +
    '  With folder:       HAT Surveillance Study | Article | C:\docs\hat-study' + #13#10 + #13#10 +
    'Categories: Article, Grant, Teaching, Software, Review, or create your own.' + #13#10 +
    'Folder: right-click the folder in Explorer → Copy as path, then paste here.' + #13#10 + #13#10 +
    'For each project Metis will: create a tracking record, write a CLAUDE.md' + #13#10 +
    'into the folder (so Claude understands it immediately), and register it' + #13#10 +
    'in Claude Desktop automatically.');
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

    { Build project list as JSON array of objects (name|category|folder format) }
    ProjectLines := '[';
    for i := 0 to 2 do
    begin
      if Trim(ProjectsPage.Values[i]) <> '' then
      begin
        { Split on | — up to 3 parts: name, category, folder }
        { Simple approach: store raw pipe-delimited string, Python will parse }
        if ProjectLines <> '[' then ProjectLines := ProjectLines + ',';
        ProjectLines := ProjectLines + '"' + Trim(ProjectsPage.Values[i]) + '"';
      end;
    end;
    ProjectLines := ProjectLines + ']';

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

procedure CurPageChanged(CurPageID: Integer);
var
  HasDash: Boolean;
  NextSteps: String;
begin
  if CurPageID = wpFinished then
  begin
    HasDash := WizardIsComponentSelected('dashboard');

    NextSteps :=
      '✓  Metis is installed.' + #13#10 + #13#10 +
      '══════════════════════════════════════════════' + #13#10 +
      '  YOUR NEXT STEPS' + #13#10 +
      '══════════════════════════════════════════════' + #13#10 + #13#10 +
      '① Install Claude Desktop (free — 2 minutes)' + #13#10 +
      '   https://claude.ai/download' + #13#10 +
      '   Open it once — Metis registers automatically.' + #13#10 + #13#10;

    if HasDash then
      NextSteps := NextSteps +
        '② Start the Metis Dashboard' + #13#10 +
        '   Double-click "Metis — Dashboard" on your desktop,' + #13#10 +
        '   or open your browser to:  http://localhost:8080' + #13#10 + #13#10 +
        '③ Complete your setup wizard' + #13#10 +
        '   Opens automatically at: http://localhost:8080/setup' + #13#10 +
        '   Also starts in Claude Desktop on first open.' + #13#10 + #13#10
    else
      NextSteps := NextSteps +
        '② Open Claude Desktop — your setup wizard starts automatically.' + #13#10 +
        '   It takes about 3 minutes and personalises Metis to your work.' + #13#10 + #13#10;

    if DemoPage.SelectedValueIndex = 0 then
      NextSteps := NextSteps +
        '── Demo workspace loaded ──────────────────────────────────' + #13#10 +
        'Explore every feature right away — realistic projects, meetings,' + #13#10 +
        'literature, and tasks are pre-loaded. Clear it any time from the' + #13#10 +
        'Metis tab → Configuration.' + #13#10 + #13#10;

    NextSteps := NextSteps +
      '══════════════════════════════════════════════' + #13#10 +
      '  WANT TO LEARN MORE?' + #13#10 +
      '══════════════════════════════════════════════' + #13#10 + #13#10 +
      'Claude Desktop (required):' + #13#10 +
      '  https://claude.ai/download' + #13#10 + #13#10 +
      'Claude Code (for developers and power users):' + #13#10 +
      '  https://docs.anthropic.com/en/docs/claude-code/getting-started' + #13#10 + #13#10 +
      'Metis documentation and source code:' + #13#10 +
      '  https://github.com/SVerITG/Metis_PH' + #13#10 + #13#10 +
      'Get your Anthropic API key (if you need a new one):' + #13#10 +
      '  https://console.anthropic.com' + #13#10 + #13#10 +
      'Questions or feedback → open an issue:' + #13#10 +
      '  https://github.com/SVerITG/Metis_PH/issues';

    WizardForm.FinishedLabel.Caption := NextSteps;
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
