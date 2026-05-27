; Metis Research Cortex — Inno Setup 6 Script
; Single compile:   ISCC.exe metis-setup.iss               → MetisSetup-full-1.0.exe
; Typed compiles:   ISCC /DDefaultType=full    metis-setup.iss → MetisSetup-full-1.0.exe
;                   ISCC /DDefaultType=standard metis-setup.iss → MetisSetup-standard-1.0.exe
;                   ISCC /DDefaultType=minimal  metis-setup.iss → MetisSetup-minimal-1.0.exe
; GitHub Actions runs all three automatically on every v* tag push.

#define MyAppName      "Metis Research Cortex"
#define MyAppVersion   "1.0"
#define MyAppPublisher "Metis Project"
#define MyAppURL       "https://github.com/<your-github-username>/Metis"

; Install type — override via /DDefaultType=standard on the command line
#ifndef DefaultType
#define DefaultType "full"
#endif

; RepoRoot = metis/ (3 levels up: installer/ -> install/ -> system/ -> metis/)
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

; Output — filename encodes the install type so releases have 3 distinct files
OutputDir=dist
OutputBaseFilename=MetisSetup-{#DefaultType}-{#MyAppVersion}

; Compression
Compression=lzma2/max
SolidCompression=yes
DiskSpanning=no

; Appearance
WizardStyle=modern

; Windows 10 minimum
MinVersion=10.0.17134

; Uninstall
UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.WelcomeText=This will install Metis Research Cortex on your computer.%n%nMetis is an AI assistant designed for researchers. It works alongside Claude AI and runs entirely on your computer — your research files never leave your machine.%n%nInstallation takes about 5 minutes.%n%nYou will need an Anthropic API key (free from console.anthropic.com).
english.CoursePageTitle=Optional: Statistics Course
english.CoursePageDesc=Include the Statistics for Epidemiology course?
english.CourseCheckboxLabel=Statistics for Epidemiology%n%nCovers: descriptive stats, inference, regression, survival analysis, and multilevel models.%nDesigned for researchers — grows as new lessons are added.

[Types]
Name: "full";     Description: "Full — dashboard + Statistics for Epidemiology course (recommended)"
Name: "standard"; Description: "Standard — AI assistant + research dashboard"
Name: "minimal";  Description: "Minimal — AI assistant only (fastest, no dashboard)"
Name: "custom";   Description: "Custom installation"; Flags: iscustom

[Components]
Name: "core";                 Description: "Metis core (agents, skills, config)";              Types: full standard minimal custom; Flags: fixed
Name: "dashboard";            Description: "Research dashboard (browser-based, 9 tabs)";       Types: full standard custom
Name: "courses";              Description: "Pre-built courses";                                  Types: full custom
Name: "courses/statistics"; Description: "Statistics for Epidemiology (full course)";  Types: full custom

[Tasks]
Name: "desktopai";     Description: "Shortcut on desktop: Open Metis AI";        GroupDescription: "Shortcuts:"
Name: "desktopdash";   Description: "Shortcut on desktop: Open Dashboard";       GroupDescription: "Shortcuts:"; Components: dashboard
Name: "startmenu";     Description: "Create Start Menu folder";                  GroupDescription: "Shortcuts:"

[Files]
; Core agents and skills
Source: "{#RepoRoot}\agents\*";           DestDir: "{app}\agents";      Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*-context.md"
Source: "{#RepoRoot}\.claude\*";          DestDir: "{app}\.claude";     Flags: ignoreversion recursesubdirs createallsubdirs

; Knowledge base — course template (always included so /course-builder has a starter)
Source: "{#RepoRoot}\knowledge\course-template\*";      DestDir: "{app}\knowledge\course-template";           Flags: ignoreversion recursesubdirs createallsubdirs

; Pre-built courses — optional component
Source: "{#RepoRoot}\knowledge\courses\statistics\*"; DestDir: "{app}\knowledge\courses\statistics";   Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: courses/statistics
Source: "{#RepoRoot}\knowledge\courses\biostatistics\*"; DestDir: "{app}\knowledge\courses\statistics"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: courses/statistics

; Placeholder courses (14 rows seeded into DB at post-install — no files needed)

; Library concepts/methods
Source: "{#RepoRoot}\knowledge\library\concepts\*";     DestDir: "{app}\knowledge\library\concepts";          Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\knowledge\library\methods\*";      DestDir: "{app}\knowledge\library\methods";           Flags: ignoreversion recursesubdirs createallsubdirs

; System config (no personal/gitignored files)
Source: "{#RepoRoot}\system\config\constitution.md";           DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\red-lines.md";              DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\token-guardrails.md";       DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\first-run-wizard.md";       DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\feature-backlog.md";        DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\implementation-plan.md";    DestDir: "{app}\system\config"; Flags: ignoreversion
Source: "{#RepoRoot}\system\config\tool-subsets.json";         DestDir: "{app}\system\config"; Flags: ignoreversion skipifsourcedoesntexist

; MCP server source
Source: "{#RepoRoot}\system\mcp-server\src\*";       DestDir: "{app}\system\mcp-server\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\system\mcp-server\pyproject.toml"; DestDir: "{app}\system\mcp-server";   Flags: ignoreversion

; Dashboard
Source: "{#RepoRoot}\system\app-py\*"; DestDir: "{app}\system\app-py"; \
  Flags: ignoreversion recursesubdirs createallsubdirs; Components: dashboard; \
  Excludes: "*.pyc,__pycache__,.venv*,*.sqlite"

; Windows launcher and install scripts
Source: "..\windows\install.ps1";            DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\bootstrap_python.ps1";           DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\download_vendor_python.ps1";     DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\windows\run-mcp.bat";            DestDir: "{app}\system\mcp-server";      Flags: ignoreversion
Source: "..\windows\run-dashboard.bat";      DestDir: "{app}\system\app-py";          Flags: ignoreversion; Components: dashboard
Source: "..\windows\run-tray.bat";           DestDir: "{app}\system\install\windows"; Flags: ignoreversion; Components: dashboard
Source: "..\tray_launcher.py";               DestDir: "{app}\system\install";         Flags: ignoreversion; Components: dashboard
; MetisTray.exe — PyInstaller bundle (built by: pyinstaller tray-launcher.spec from system/install/)
; Only included when dist/MetisTray.exe exists. Skip silently if not yet compiled.
Source: "..\dist\MetisTray.exe";             DestDir: "{app}\system\install\windows"; Flags: ignoreversion skipifsourcedoesntexist; Components: dashboard
Source: "..\vendor_download.py";             DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\config_merger.py";               DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\seed_epi_base.py";               DestDir: "{app}\system\install";         Flags: ignoreversion
Source: "..\build_knowledge_db.py";          DestDir: "{app}\system\install";         Flags: ignoreversion

; Bundled Python embeddable (offline fallback — created by download_vendor_python.ps1)
Source: "..\vendor\python-embed.zip";        DestDir: "{app}\vendor";                 Flags: ignoreversion skipifsourcedoesntexist
Source: "..\vendor\get-pip.py";              DestDir: "{app}\vendor";                 Flags: ignoreversion skipifsourcedoesntexist

; CONTRIBUTING + README
Source: "{#RepoRoot}\..\CONTRIBUTING.md"; DestDir: "{app}";  Flags: ignoreversion skipifsourcedoesntexist
Source: "{#RepoRoot}\..\README.md";       DestDir: "{app}";  Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
; Personal folders — created empty, never committed
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
Name: "{group}\Metis — Open AI";        Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; \
  Tasks: startmenu; Comment: "Open Metis AI assistant"
Name: "{group}\Metis — Dashboard";      Filename: "wscript.exe"; \
  Parameters: """{app}\system\install\windows\launch-dashboard-silent.vbs"""; \
  IconFilename: "{app}\system\install\windows\metis.ico"; IconIndex: 0; \
  Tasks: startmenu; Components: dashboard; Comment: "Open Metis Research Dashboard"
Name: "{group}\Uninstall Metis";        Filename: "{uninstallexe}"; Tasks: startmenu

; Desktop
Name: "{autodesktop}\Metis — Open AI";      Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; \
  Tasks: desktopai
Name: "{autodesktop}\Metis";    Filename: "wscript.exe"; \
  Parameters: """{app}\system\install\windows\launch-dashboard-silent.vbs"""; \
  IconFilename: "{app}\system\install\windows\metis.ico"; IconIndex: 0; \
  Tasks: desktopdash; Components: dashboard; Comment: "Open Metis Research Dashboard"

[Run]
; Step 0: Python bootstrap (M11.4) — tries winget, python.org, then bundled embed
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\bootstrap_python.ps1"" -InstallDir ""{app}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Setting up Python (checking installed versions)…"

; Step 1 (dashboard): full install — Python, venv, MCP, Claude Desktop config
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -SkipPython -SkipClaude -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Installing Metis (2–4 minutes)…"; \
  Components: dashboard

; Step 1 (no dashboard): MCP only — skip Python, skip dashboard
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -Stage1Only -SkipPython -SkipClaude -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Configuring Metis AI assistant…"; \
  Components: not dashboard

; Stage 1 only: skip Python, just configure
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -Stage1Only -SkipClaude -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Configuring Metis AI assistant…"; \
  Components: not dashboard

; Step 2 (full): seed Statistics for Epidemiology course into SQLite
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""& {{ $py = $env:METIS_PYTHON; if (-not $py) {{ $py = 'python' }}; & $py '{app}\system\install\seed_epi_base.py' --db '{app}\system\app\data\metis.sqlite' --quiet }}"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Seeding Statistics for Epidemiology course…"; \
  Components: courses/statistics

; Step 3 (full/standard): Build PDF knowledge database — local embeddings, no API key needed
; Runs only when the library folder has PDFs. Skips gracefully if library is empty.
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""& {{ $py = $env:METIS_PYTHON; if (-not $py) {{ $py = 'python' }}; & $py '{app}\system\install\build_knowledge_db.py' --library-dir '{app}\knowledge\library' --db '{app}\system\app\data\metis.sqlite' --quiet }}"""; \
  Flags: waituntilterminated runhidden; \
  StatusMsg: "Building knowledge database (5–15 min, uses your CPU — Metis will learn from all included documents)…"; \
  Components: dashboard

; Launch Claude Desktop
Filename: "{pf}\Anthropic\Claude\Claude.exe"; \
  Description: "Launch Claude Desktop (Metis starts automatically)"; \
  Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\system\mcp-server\.venv-win"
Type: files;          Name: "{userappdata}\Claude\claude_desktop_config.json.metis-backup"

[Code]
var
  ApiKeyPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  // Welcome message override
  WizardForm.WelcomeLabel2.Caption := CustomMessage('WelcomeText');

  // Pre-select components matching the compiled install type
  // (user can still change in the wizard)
#if DefaultType == "minimal"
  WizardSelectComponents('');
#elif DefaultType == "standard"
  WizardSelectComponents('dashboard');
#else
  WizardSelectComponents('dashboard,courses,courses/statistics');
#endif

  // API key input page — shown after component selection
  ApiKeyPage := CreateInputQueryPage(
    wpSelectTasks,
    'Anthropic API Key',
    'Required to connect Metis to Claude AI.',
    'Your key is stored only on this computer and is never uploaded or shared.' + #13#10 +
    'Get a free key at: https://console.anthropic.com' + #13#10 + #13#10 +
    'The key looks like: sk-ant-api03-...');
  ApiKeyPage.Add('Paste your API key here:', False);
end;

function GetApiKey(Param: String): String;
begin
  Result := Trim(ApiKeyPage.Values[0]);
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
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ApiKey, EnvDir, EnvFile, EnvContent: String;
  StateFile, Profile, StateContent, CoursesStr, DashStr: String;
  HasDash, HasCourse: Boolean;
begin
  if CurStep = ssPostInstall then
  begin
    ApiKey := Trim(ApiKeyPage.Values[0]);

    // Write .env file with API key and root path
    EnvDir  := ExpandConstant('{app}\system');
    EnvFile := EnvDir + '\.env';
    ForceDirectories(EnvDir);

    EnvContent := 'ANTHROPIC_API_KEY=' + ApiKey + #13#10 +
                  'METIS_RC_ROOT=' + ExpandConstant('{app}') + #13#10;
    SaveStringToFile(EnvFile, EnvContent, False);

    // Write first-run marker
    SaveStringToFile(ExpandConstant('{app}\system\config\.first-run'), '', False);

    // Write install-state.json reflecting chosen components
    StateFile  := ExpandConstant('{app}\system\config\install-state.json');
    HasDash    := WizardIsComponentSelected('dashboard');
    HasCourse  := WizardIsComponentSelected('courses/statistics');
    Profile    := 'standard';
    if HasDash and HasCourse then Profile := 'full'
    else if not HasDash then Profile := 'mcp-only';
    if HasCourse then CoursesStr := '"statistics"' else CoursesStr := '';
    if HasDash then DashStr := 'true' else DashStr := 'false';
    StateContent :=
      '{' + #13#10 +
      '  "profile": "' + Profile + '",' + #13#10 +
      '  "version": "' + '{#MyAppVersion}' + '",' + #13#10 +
      '  "installed_at": "' + GetDateTimeString('yyyy/mm/dd', '-', ':') + '",' + #13#10 +
      '  "courses_included": [' + CoursesStr + '],' + #13#10 +
      '  "components": {' + #13#10 +
      '    "mcp_server": true,' + #13#10 +
      '    "dashboard": ' + DashStr + ',' + #13#10 +
      '    "hooks": true,' + #13#10 +
      '    "windows_task_scheduler": false,' + #13#10 +
      '    "nssm_service": false,' + #13#10 +
      '    "docker": false' + #13#10 +
      '  }' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(StateFile, StateContent, False);
  end;
end;

// Install Claude Desktop before files are extracted
procedure CurPageChanged(CurPageID: Integer);
begin
  // Nothing needed — Claude Desktop install handled by PowerShell post-install script
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  // Check Windows version
  if not (GetWindowsVersion >= $0A000000) then
  begin
    MsgBox('Metis requires Windows 10 or later.', mbError, MB_OK);
    Result := False;
  end;
end;
