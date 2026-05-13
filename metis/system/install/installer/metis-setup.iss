; Metis Research Cortex — Inno Setup 6 Script
; Compile: ISCC.exe metis-setup.iss
; Output:  dist\MetisSetup-1.0.exe

#define MyAppName      "Metis Research Cortex"
#define MyAppVersion   "1.0"
#define MyAppPublisher "Metis Project"
#define MyAppURL       "https://github.com/SVerITG/Metis_PH"

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

; Output
OutputDir=dist
OutputBaseFilename=MetisSetup-{#MyAppVersion}

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

[Types]
Name: "standard"; Description: "Standard — AI assistant + research dashboard (recommended)"
Name: "minimal";  Description: "Minimal — AI assistant only (fastest, no dashboard)"

[Components]
Name: "core";       Description: "Metis core (agents, skills, config)"; Types: standard minimal; Flags: fixed
Name: "dashboard";  Description: "Research dashboard (browser app)";     Types: standard

[Tasks]
Name: "desktopai";     Description: "Shortcut on desktop: Open Metis AI";        GroupDescription: "Shortcuts:"
Name: "desktopdash";   Description: "Shortcut on desktop: Open Dashboard";       GroupDescription: "Shortcuts:"; Components: dashboard
Name: "startmenu";     Description: "Create Start Menu folder";                  GroupDescription: "Shortcuts:"

[Files]
; Core agents and skills
Source: "{#RepoRoot}\agents\*";           DestDir: "{app}\agents";      Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*-context.md"
Source: "{#RepoRoot}\.claude\*";          DestDir: "{app}\.claude";     Flags: ignoreversion recursesubdirs createallsubdirs

; Knowledge base (courses + library concepts/methods — no personal disease-area files)
Source: "{#RepoRoot}\knowledge\courses\*";              DestDir: "{app}\knowledge\courses";                   Flags: ignoreversion recursesubdirs createallsubdirs
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

; Windows launcher scripts
Source: "..\windows\install.ps1";        DestDir: "{app}\system\install\windows"; Flags: ignoreversion
Source: "..\windows\run-mcp.bat";        DestDir: "{app}\system\mcp-server";      Flags: ignoreversion
Source: "..\windows\run-dashboard.bat";  DestDir: "{app}\system\app-py";          Flags: ignoreversion; Components: dashboard

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
Name: "{group}\Metis — Dashboard";      Filename: "{app}\system\app-py\run-windows.bat"; \
  Tasks: startmenu; Components: dashboard
Name: "{group}\Uninstall Metis";        Filename: "{uninstallexe}"; Tasks: startmenu

; Desktop
Name: "{autodesktop}\Metis — Open AI";      Filename: "{commonpf}\Anthropic\Claude\Claude.exe"; \
  Tasks: desktopai
Name: "{autodesktop}\Metis — Dashboard";    Filename: "{app}\system\app-py\run-windows.bat"; \
  Tasks: desktopdash; Components: dashboard

[Run]
; Post-install: run PowerShell to install Python, MCP server, configure Claude Desktop
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -SkipClaude -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Installing Python and configuring Metis (2–4 minutes)…"; \
  Components: dashboard

; Stage 1 only: skip Python, just configure
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\system\install\windows\install.ps1"" -Stage1Only -SkipClaude -InstallDir ""{app}"" -ApiKey ""{code:GetApiKey}"""; \
  Flags: waituntilterminated; \
  StatusMsg: "Configuring Metis AI assistant…"; \
  Components: not dashboard

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
