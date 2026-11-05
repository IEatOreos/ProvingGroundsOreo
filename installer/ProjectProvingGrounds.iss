; Project Proving Grounds' Windows installer (Inno Setup 6). Built by tools/build_installer.py, which stages the files
; (Payload) and passes the version: ISCC /DAppVersion=0.1.0 /DPayload=<folder> /DBuildDir=<folder> this file.
;
; Installs for the current user (no administrator rights needed) into %LOCALAPPDATA%\Programs\Project Proving Grounds,
; with a Start Menu shortcut to the launcher and an optional desktop one. A page of its own asks for the Windows Security
; exclusion for the mod's folder (native\bin), which the bots need: Windows Security deletes the injector that loads the
; mod into MCC. It is ticked, unticking it asks again, and it is added before the files are copied (administrator
; permission asked then); an update over an install that has it skips the page. Silent installs add it unless
; /EXCLUSION=no. Uninstalling removes the exclusion again and asks whether to keep the player's LiDAR scans, learned map
; data and recorded matches.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef Payload
  #error Payload (the staged files) must be given: ISCC /DPayload=<folder>
#endif
#ifndef BuildDir
  #define BuildDir "."
#endif

[Setup]
AppId={{8C3B2F7E-5A41-4D8E-9C6B-1F2E3D4C5B6A}
AppName=Project Proving Grounds
AppVersion={#AppVersion}
AppVerName=Project Proving Grounds {#AppVersion}
AppPublisher=The Project Proving Grounds contributors
DefaultDirName={autopf}\Project Proving Grounds
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#BuildDir}
OutputBaseFilename=ProjectProvingGrounds-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile={#BuildDir}\license.txt
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\installer\icon.ico
UninstallDisplayName=Project Proving Grounds
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[InstallDelete]
; an update first clears the previous version's code and documents, so files a release dropped do not stay behind (the
; player's logs, maps, LiDAR scans and the art the setup built are kept)
Type: filesandordirs; Name: "{app}\docs"
Type: filesandordirs; Name: "{app}\ghidra"
Type: filesandordirs; Name: "{app}\native\tests"
Type: filesandordirs; Name: "{app}\tools\menu_titles"
Type: filesandordirs; Name: "{app}\tools\__pycache__"
Type: filesandordirs; Name: "{app}\brain\__pycache__"
Type: files; Name: "{app}\tools\*.py"
Type: files; Name: "{app}\tools\*.html"
Type: files; Name: "{app}\tools\*.ps1"
Type: files; Name: "{app}\brain\*.py"
Type: files; Name: "{app}\native\*.cpp"
Type: files; Name: "{app}\native\*.h"
Type: files; Name: "{app}\native\*.bat"
Type: files; Name: "{app}\CODE_OF_CONDUCT.md"
Type: files; Name: "{app}\CONTRIBUTING.md"
Type: files; Name: "{app}\SECURITY.md"
Type: files; Name: "{app}\requirements*.txt"

[Files]
Source: "{#Payload}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Project Proving Grounds"; Filename: "{app}\python\pythonw.exe"; Parameters: "-I ""{app}\tools\launcher.py"""; WorkingDir: "{app}"; IconFilename: "{app}\installer\icon.ico"; Comment: "PvP bots for Halo: The Master Chief Collection"
Name: "{autodesktop}\Project Proving Grounds"; Filename: "{app}\python\pythonw.exe"; Parameters: "-I ""{app}\tools\launcher.py"""; WorkingDir: "{app}"; IconFilename: "{app}\installer\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: "-I ""{app}\tools\launcher.py"" --setup"; WorkingDir: "{app}"; Description: "Open Project Proving Grounds and run the first-time setup"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; the app window's WebView2 data (cache, settings: tools/appwindow.py)
Type: filesandordirs; Name: "{localappdata}\ProjectProvingGrounds"

[Code]
const
  MARK = '\installer\windows-security-exclusion.txt';

function Quoted(S: String): String;          { a PowerShell single-quoted string: its quotes doubled }
begin
  Result := S;
  StringChangeEx(Result, '''', '''''', True);
  Result := '''' + Result + '''';
end;

function RunElevatedPowerShell(Command: String): Boolean;
var
  Code: Integer;
begin
  Result := ShellExec('runas', 'powershell.exe', '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "' + Command + '"',
                      '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0);
end;

function PowerShell(Command: String): Integer;
begin
  if not Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "' + Command + '"',
              '', SW_HIDE, ewWaitUntilTerminated, Result) then
    Result := -1;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not DirExists(ExpandConstant('{app}\native')) then
    exit;
  // an earlier install being updated: MCC with the bots loaded holds botcore.dll; the mod's own programs (the
  // launcher, the tools' servers, their windows) have no window Restart Manager can close, so they are ended here
  if PowerShell('if (Get-Process MCC-Win64-Shipping -ErrorAction SilentlyContinue) { exit 3 }') = 3 then
    Result := 'Close Halo: The Master Chief Collection first (the bots are loaded into it), then run Setup again.'
  else
    PowerShell('Get-Process | Where-Object { $_.Path -like ' + Quoted(ExpandConstant('{app}') + '\*') + ' } | Stop-Process -Force');
end;

var
  SecurityPage: TInputOptionWizardPage;
  ExclusionAdded: Boolean;

procedure InitializeWizard;
begin
  SecurityPage := CreateInputOptionPage(wpSelectTasks, 'Windows Security exclusion (required)',
    'The bots can''t load into the game without it.',
    'Project Proving Grounds loads its bots into Halo: MCC with a small program called an injector. Windows Security ' +
    'treats injectors as suspicious and usually deletes them, and then the bots can''t load.' + #13#10 + #13#10 +
    'Setup adds one exclusion, for the mod''s own program folder (native\bin), and nothing else. Windows asks for ' +
    'administrator permission when Setup adds it, and uninstalling removes it again.' + #13#10 + #13#10 +
    'Using another antivirus? Add the same folder to its exclusions after installing.',
    False, False);
  SecurityPage.Add('Add the Windows Security exclusion for the mod''s folder (required)');
  SecurityPage.Values[0] := True;
end;

function HasExclusion: Boolean;                { added by an earlier install of this folder }
begin
  Result := FileExists(ExpandConstant('{app}') + MARK);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = SecurityPage.ID) and HasExclusion;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = SecurityPage.ID) and not SecurityPage.Values[0] then
    Result := MsgBox('Without the exclusion, Windows Security will most likely delete the injector, and the bots won''t ' +
                     'load into the game.' + #13#10 + #13#10 + 'You can add it yourself later: Windows Security > Virus ' +
                     '& threat protection > Manage settings > Exclusions.' + #13#10 + #13#10 +
                     'Continue without it?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

function WantExclusion: Boolean;
begin
  if HasExclusion then
    Result := False
  else if WizardSilent then
    Result := CompareText(ExpandConstant('{param:exclusion|yes}'), 'no') <> 0
  else
    Result := SecurityPage.Values[0];
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Dir: String;
begin
  Dir := ExpandConstant('{app}\native\bin');
  // before the files are copied, so Windows Security does not delete the injector while they are
  if (CurStep = ssInstall) and WantExclusion then
  begin
    ExclusionAdded := RunElevatedPowerShell('Add-MpPreference -ExclusionPath ' + Quoted(Dir));
    if not ExclusionAdded then
      SuppressibleMsgBox('The Windows Security exclusion was not added (permission was not given, or another antivirus ' +
                         'manages Windows Security). The bots need it to load.' + #13#10 + #13#10 + 'To add it yourself: ' +
                         'Windows Security > Virus & threat protection > Manage settings > Exclusions > Add or remove ' +
                         'exclusions > Add an exclusion > Folder, and choose:' + #13#10 + Dir, mbInformation, MB_OK, IDOK);
  end;
  if (CurStep = ssPostInstall) and ExclusionAdded then
    SaveStringToFile(ExpandConstant('{app}') + MARK, Dir, False);
end;

var
  KeepData: Boolean;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dir: AnsiString;
begin
  if CurUninstallStep = usUninstall then
  begin
    // (the mod's programs still running, e.g. a tool's server, would keep their files)
    PowerShell('Get-Process | Where-Object { $_.Path -like ' + Quoted(ExpandConstant('{app}') + '\*') + ' } | Stop-Process -Force');
    if LoadStringFromFile(ExpandConstant('{app}') + MARK, Dir) then
      RunElevatedPowerShell('Remove-MpPreference -ExclusionPath ' + Quoted(String(Dir)));
    // (a silent uninstall keeps them: /SUPPRESSMSGBOXES answers Yes)
    KeepData := SuppressibleMsgBox('Keep your LiDAR scans, what the bots learned on each map and your recorded matches?'
                                   + #13#10 + #13#10 + 'Yes keeps them in ' + ExpandConstant('{app}') + ' (maps and logs ' +
                                   'folders) for a later install; No deletes everything.', mbConfirmation, MB_YESNO,
                                   IDYES) = IDYES;
  end;
  if CurUninstallStep = usPostUninstall then
  begin
    if KeepData then
    begin
      DelTree(ExpandConstant('{app}\native'), True, True, True);
      DelTree(ExpandConstant('{app}\python'), True, True, True);
      DelTree(ExpandConstant('{app}\tools'), True, True, True);
      DelTree(ExpandConstant('{app}\brain'), True, True, True);
    end
    else
      DelTree(ExpandConstant('{app}'), True, True, True);
  end;
end;
