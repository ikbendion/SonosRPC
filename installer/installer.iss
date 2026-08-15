; Inno Setup script for Sonos Discord Presence.
;
; Installs per-user to {localappdata} so no admin/UAC prompt is needed --
; this is a single-user tray utility, and the "Start with Windows" feature
; already writes to HKCU, so a whole-machine Program Files install would
; just add elevation friction for no real benefit.
;
; Build the exe first (see build/build.py), then compile this with:
;   iscc installer\installer.iss

#define MyAppName "Sonos Discord Presence"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "ikbendion"
#define MyAppExeName "SonosDiscordPresence.exe"
#define MyAppUrl "https://github.com/ikbendion/sonosrpc"

[Setup]
AppId={{9C6F0F1B-6B6E-4A1E-9C63-6E2E8E9B4E1A}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppUrl}
DefaultDirName={localappdata}\SonosDiscordPresence
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=SonosDiscordPresence-Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startupicon"; Description: "Launch {#MyAppName} automatically when Windows starts"; GroupDescription: "Additional options:"

[Files]
Source: "..\dist\SonosDiscordPresence.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "SonosDiscordPresence"; ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The exe itself; config/log files are handled explicitly in code below
; so the user gets a chance to keep them.
Type: files; Name: "{app}\{#MyAppExeName}"

[Code]
function InitializeUninstall(): Boolean;
begin
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    ConfigDir := ExpandConstant('{userappdata}\SonosDiscordPresence');
    if DirExists(ConfigDir) then
    begin
      if MsgBox('Also delete your Sonos Discord Presence settings (Discord Client ID, ' +
                'selected speaker) stored in' + #13#10 + ConfigDir + '?',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(ConfigDir, True, True, True);
      end;
    end;
  end;
end;
