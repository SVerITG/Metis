; Metis Research Cortex — Inno Setup 6 Script
; Compile:       ISCC.exe metis-setup.iss  →  MetisSetup-1.0.exe
; GitHub Actions compiles automatically on every v* tag push.

#define MyAppName      "Metis — Public Health Research Cortex"
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
InfoBeforeFile=metis-info.txt
InfoAfterFile=metis-after.txt

UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.WelcomeText=Welcome to Metis — your AI research companion.%n%nMetis gives every Claude conversation a persistent memory of your domain, your papers, your projects, and your working history. The longer you use it, the better every response gets — because Metis knows you better, not because the AI changed.%n%nYou don't need to follow developments in AI. Metis does that for you.%n%nEverything runs on your computer. Your files never leave your machine.%n%n────────────────────────────────────────────%n%nThis installer will:%n  1. Install the Metis AI core (MCP server + 34 specialist agents)%n  2. Optionally install the 9-tab research dashboard%n  3. Ask you a few questions to personalise Metis to your work%n%nInstallation takes 5–15 minutes depending on your connection.%nYou will need a free Anthropic API key — instructions are on the next page.

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
Source: "..\windows\launch-dashboard.ps1";      DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
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
Name: "{group}\Metis — Dashboard";  Filename: "powershell.exe"; \
  Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\system\install\windows\launch-dashboard.ps1"""; \
  IconFilename: "{app}\system\install\windows\metis-brain.ico"; IconIndex: 0; \
  Tasks: startmenu; Components: dashboard
Name: "{group}\Uninstall Metis";    Filename: "{uninstallexe}"; Tasks: startmenu

; Desktop — Claude shortcut only created if Claude Desktop is installed
Name: "{autodesktop}\Metis — Open AI"; Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; Tasks: desktopai; \
  Check: FileExists(ExpandConstant('{commonpf}\Anthropic\Claude\Claude.exe'))
Name: "{autodesktop}\Metis";           Filename: "powershell.exe"; \
  Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\system\install\windows\launch-dashboard.ps1"""; \
  IconFilename: "{app}\system\install\windows\metis-brain.ico"; IconIndex: 0; \
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
{ ── Page variables ──────────────────────────────────────────────────────── }
var
  McpConsentPage: TInputOptionWizardPage;
  DemoPage:       TInputOptionWizardPage;
  ApiKeyPage:     TInputQueryWizardPage;
  AboutPage:      TInputQueryWizardPage;
  ResearchPage:   TInputQueryWizardPage;
  StylePage:      TInputOptionWizardPage;
  ProjectsPage:   TInputQueryWizardPage;
  FoldersPage:    TInputDirWizardPage;

{ ── Pascal helpers ──────────────────────────────────────────────────────── }
function ShouldSeedDemo: Boolean;
begin
  Result := (DemoPage.SelectedValueIndex = 0);
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

{ ── Wizard initialisation ───────────────────────────────────────────────── }
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption := CustomMessage('WelcomeText');

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 1 — MCP SERVER AUTHORISATION
    Shown right after the component selection page.
    Explains what the MCP server is and asks for explicit consent.
    ═══════════════════════════════════════════════════════════════════════ }
  McpConsentPage := CreateInputOptionPage(
    wpSelectComponents,
    'Authorise Background Component',
    'The MCP server — what it does and what you are authorising.',
    'Metis works by installing a small background program called an MCP server' + #13#10 +
    '(MCP = Model Context Protocol, an open standard from Anthropic).' + #13#10 +
    'This program sits between Claude and your research files. When you ask Claude' + #13#10 +
    'a question, the MCP server retrieves the right context from your notes,' + #13#10 +
    'papers, and history — and returns it to Claude on your behalf.' + #13#10 +
    '' + #13#10 +
    'What the MCP server CAN do:' + #13#10 +
    '  ✓  Read and write files in your Metis research folder' + #13#10 +
    '  ✓  Connect to Claude when you open Claude Desktop or Claude Code' + #13#10 +
    '  ✓  Build and maintain your personal knowledge base locally' + #13#10 +
    '  ✓  Run lightweight background scans (news, papers) on a schedule' + #13#10 +
    '' + #13#10 +
    'What the MCP server CANNOT do:' + #13#10 +
    '  ✗  Access files outside your Metis folder without your permission' + #13#10 +
    '  ✗  Send your research data to any server (everything stays local)' + #13#10 +
    '  ✗  Run without Claude being open (it is not a persistent background service)' + #13#10 +
    '' + #13#10 +
    'You can remove the MCP server at any time: Windows Settings → Apps → Metis' + #13#10 +
    'or by running the Metis uninstaller.',
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
    'A demo workspace pre-loads a realistic research scenario:' + #13#10 +
    '  • 3 example projects (surveillance study, literature review, grant)' + #13#10 +
    '  • Sample meeting notes with action items' + #13#10 +
    '  • A small example literature library' + #13#10 +
    '  • Some open tasks and ideas' + #13#10 +
    '' + #13#10 +
    'This lets you try every dashboard tab immediately without having to add' + #13#10 +
    'your own content first.' + #13#10 +
    '' + #13#10 +
    'You can clear the demo content and replace it with your own work at any time' + #13#10 +
    'from the Metis dashboard (Settings → Clear demo content).',
    True, False);
  DemoPage.Add('Yes — load demo content  (recommended for first-time users)');
  DemoPage.Add('No  — start with a blank workspace');
  DemoPage.SelectedValueIndex := 0;

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 3 — ANTHROPIC API KEY
    ═══════════════════════════════════════════════════════════════════════ }
  ApiKeyPage := CreateInputQueryPage(
    DemoPage.ID,
    'Anthropic API Key',
    'Connect Metis to Claude AI — takes 2 minutes.',
    'Metis uses the Anthropic API to power its 34 specialist agents' + #13#10 +
    '(Epidemiologist, Writing Partner, Librarian, Methods Coach, and more).' + #13#10 +
    'You need a free API key from Anthropic to use them.' + #13#10 +
    '' + #13#10 +
    'HOW TO GET YOUR FREE API KEY' + #13#10 +
    '  1. Open your browser and go to:  https://console.anthropic.com' + #13#10 +
    '  2. Sign up or log in (free — no credit card needed to start)' + #13#10 +
    '  3. Click "API Keys" in the left sidebar, then "Create Key"' + #13#10 +
    '  4. Copy the key and paste it in the box below' + #13#10 +
    '' + #13#10 +
    'COSTS' + #13#10 +
    '  Most daily research tasks cost a few cents. Metis shows you exactly' + #13#10 +
    '  what each agent run costs — there are no hidden charges.' + #13#10 +
    '  You can set a monthly spending limit in the Anthropic console.' + #13#10 +
    '' + #13#10 +
    'SECURITY' + #13#10 +
    '  Your key is stored only on this computer in a local .env file.' + #13#10 +
    '  It is never uploaded, shared, or sent anywhere except to Anthropic''s' + #13#10 +
    '  own API when you run an agent.' + #13#10 +
    '' + #13#10 +
    'The key looks like:   sk-ant-api03-…');
  ApiKeyPage.Add('Paste your Anthropic API key here:', False);

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 4 — ABOUT YOU
    ═══════════════════════════════════════════════════════════════════════ }
  AboutPage := CreateInputQueryPage(
    ApiKeyPage.ID,
    'About You',
    'Help Metis get to know you — this takes about 1 minute.',
    'Metis will use your answers to:' + #13#10 +
    '  • Address you by name in every conversation' + #13#10 +
    '  • Calibrate how it communicates (technical depth, terminology)' + #13#10 +
    '  • Understand your institutional context when reviewing documents' + #13#10 +
    '  • Route questions to the most relevant specialist agent' + #13#10 +
    '' + #13#10 +
    'You can update any of this later by typing  /metis_config  in Claude.' + #13#10 +
    '' + #13#10 +
    'Your name and institution never leave this computer — they are used' + #13#10 +
    'only to personalise how Metis talks to you.');
  AboutPage.Add('Your full name:', False);
  AboutPage.Add('Institution or organisation (optional):', False);
  AboutPage.Add('Your role or title (e.g. PhD researcher, epidemiologist, professor):', False);

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 5 — YOUR RESEARCH
    ═══════════════════════════════════════════════════════════════════════ }
  ResearchPage := CreateInputQueryPage(
    AboutPage.ID,
    'Your Research Domain',
    'Tell Metis what field you work in.',
    'Metis uses your field and topics to:' + #13#10 +
    '  • Set up daily literature alerts (PubMed, OpenAlex)' + #13#10 +
    '  • Load the right specialist agents by default' + #13#10 +
    '  • Use accurate domain terminology in responses' + #13#10 +
    '  • Build a tailored morning brief every day' + #13#10 +
    '' + #13#10 +
    'EXAMPLES' + #13#10 +
    '  Primary field:     Epidemiology / Global Health / Spatial statistics' + #13#10 +
    '  Key topics:        NTDs, HAT surveillance, vector control, DRC' + #13#10 +
    '  Tools:             R, QGIS, DHIS2, SaTScan' + #13#10 +
    '' + #13#10 +
    'You can refine these any time via  /metis_config  in Claude.');
  ResearchPage.Add('Primary research field:', False);
  ResearchPage.Add('Key topics (comma-separated):', False);
  ResearchPage.Add('Tools and software you use regularly (comma-separated):', False);

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 6 — WORKING STYLE
    ═══════════════════════════════════════════════════════════════════════ }
  StylePage := CreateInputOptionPage(
    ResearchPage.ID,
    'Communication Style',
    'How should Metis give you feedback?',
    'Metis will review your methods, critique your writing, and challenge your' + #13#10 +
    'thinking. Choose the approach that works best for you.' + #13#10 +
    '' + #13#10 +
    'This affects how agents like the Epidemiologist, Writing Partner, and' + #13#10 +
    'Methods Coach communicate with you — not what they know.' + #13#10 +
    '' + #13#10 +
    'You can change this at any time from the Metis tab → Appearance.',
    True, False);
  StylePage.Add('Supportive — always encouraging; critiques are wrapped in positive framing');
  StylePage.Add('Direct — honest and clear; calls out problems without softening  (recommended)');
  StylePage.Add('Blunt — no hedging; challenges assumptions; short and straight');
  StylePage.SelectedValueIndex := 1;

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 7 — ACTIVE PROJECTS (names + categories)
    ═══════════════════════════════════════════════════════════════════════ }
  ProjectsPage := CreateInputQueryPage(
    StylePage.ID,
    'Your Active Projects',
    'Tell Metis what you are currently working on.',
    'Metis creates a tracking record for each project:' + #13#10 +
    '  • Writes a CLAUDE.md into the project folder — so Claude understands' + #13#10 +
    '    the project the moment you open it' + #13#10 +
    '  • Registers the project in Claude Desktop automatically' + #13#10 +
    '  • Adds it to the dashboard for task tracking and progress updates' + #13#10 +
    '' + #13#10 +
    'FORMAT:   Project name | Category' + #13#10 +
    '  Just a name:         HAT Surveillance Study' + #13#10 +
    '  With category:       HAT Surveillance Study | Article' + #13#10 +
    '' + #13#10 +
    'Categories: Article, Grant, Teaching, Software, Review — or create your own.' + #13#10 +
    '' + #13#10 +
    'Folders are selected on the next page.' + #13#10 +
    'You can add unlimited projects later from the dashboard (localhost:8080/setup).');
  ProjectsPage.Add('Project 1  (name | category):', False);
  ProjectsPage.Add('Project 2  (optional):', False);
  ProjectsPage.Add('Project 3  (optional):', False);

  { ═══════════════════════════════════════════════════════════════════════
    PAGE 8 — PROJECT FOLDERS  (folder browse with native OS dialog)
    ═══════════════════════════════════════════════════════════════════════ }
  FoldersPage := CreateInputDirPage(
    ProjectsPage.ID,
    'Project Folders',
    'Select the folder on your computer for each project (optional).',
    'Metis will scan each folder you select to understand what work you' + #13#10 +
    'have already done — commits, modified files, and notes.' + #13#10 +
    '' + #13#10 +
    'Click the "..." button to browse for the folder on your computer.' + #13#10 +
    '' + #13#10 +
    'Tip: this is the root folder of the project — for example:' + #13#10 +
    '  C:\Users\YourName\Documents\HAT-Surveillance' + #13#10 +
    '' + #13#10 +
    'Leave a field blank if the project has no local folder yet,' + #13#10 +
    'or if you prefer to add the folder later from the dashboard.',
    True,
    'The folder you entered does not exist. Leave it blank to skip it, or create the folder first.');
  FoldersPage.Add('Project 1 folder (optional):');
  FoldersPage.Add('Project 2 folder (optional):');
  FoldersPage.Add('Project 3 folder (optional):');
end;

{ ── Validation on Next ──────────────────────────────────────────────────── }
function NextButtonClick(CurPageID: Integer): Boolean;
var
  ApiKey: String;
begin
  Result := True;

  if CurPageID = McpConsentPage.ID then
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
    if Length(ApiKey) < 20 then
    begin
      MsgBox(
        'Please enter a valid Anthropic API key before continuing.' + #13#10 + #13#10 +
        'Get one free at: https://console.anthropic.com' + #13#10 +
        '(sign up → API Keys → Create Key)',
        mbError, MB_OK);
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
      MsgBox('Please enter your name before continuing.', mbError, MB_OK);
      Result := False;
    end
    else if Trim(AboutPage.Values[2]) = '' then
    begin
      MsgBox('Please enter your role or title before continuing.', mbError, MB_OK);
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
  PipeParts: TStringList;
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

    { Build project list as JSON array.
      Each entry combines the name|category from ProjectsPage and the
      folder path from FoldersPage into a single JSON object. }
    ProjectLines := '[';
    PipeParts := TStringList.Create;
    PipeParts.Delimiter := '|';
    for i := 0 to 2 do
    begin
      if Trim(ProjectsPage.Values[i]) <> '' then
      begin
        PipeParts.DelimitedText := ProjectsPage.Values[i];
        ProjName := Trim(PipeParts[0]);
        if PipeParts.Count > 1 then ProjCat := Trim(PipeParts[1])
        else ProjCat := '';
        ProjFolder := Trim(FoldersPage.Values[i]);

        if ProjectLines <> '[' then ProjectLines := ProjectLines + ',' + #13#10;
        ProjectLines := ProjectLines +
          '  {"name":"' + JsonEsc(ProjName) + '"' +
          ',"category":"' + JsonEsc(ProjCat) + '"' +
          ',"folder":"' + JsonEsc(ProjFolder) + '"}';
      end;
    end;
    PipeParts.Free;
    ProjectLines := ProjectLines + #13#10 + ']';

    { Write system/.env }
    EnvDir  := ExpandConstant('{app}\system');
    ForceDirectories(EnvDir);
    EnvFile    := EnvDir + '\.env';
    EnvContent := 'ANTHROPIC_API_KEY=' + ApiKey + #13#10 +
                  'METIS_RC_ROOT=' + ExpandConstant('{app}') + #13#10;
    SaveStringToFile(EnvFile, EnvContent, False);

    { Write system/wizard-answers.json for process_wizard_answers.py }
    AnswersFile    := EnvDir + '\wizard-answers.json';
    AnswersContent :=
      '{' + #13#10 +
      '  "name": "'        + JsonEsc(Trim(AboutPage.Values[0]))    + '",' + #13#10 +
      '  "institution": "' + JsonEsc(Trim(AboutPage.Values[1]))    + '",' + #13#10 +
      '  "role": "'        + JsonEsc(Trim(AboutPage.Values[2]))    + '",' + #13#10 +
      '  "field": "'       + JsonEsc(Trim(ResearchPage.Values[0])) + '",' + #13#10 +
      '  "topics": "'      + JsonEsc(Trim(ResearchPage.Values[1])) + '",' + #13#10 +
      '  "tools": "'       + JsonEsc(Trim(ResearchPage.Values[2])) + '",' + #13#10 +
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
  if not (GetWindowsVersion >= $0A000000) then
  begin
    MsgBox('Metis requires Windows 10 (version 1803) or later.', mbError, MB_OK);
    Result := False;
  end;
end;
