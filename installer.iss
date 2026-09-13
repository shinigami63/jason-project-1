; Inno Setup script for the Kebbet Zamen app.
;
; Built by .github/workflows/build.yml, which passes the version in:
;   ISCC /DAppVersion=1.0.57 installer.iss
;
; Installs per-user into LocalAppData so it never asks for administrator
; rights -- the exe is unsigned, and an elevation prompt for an unsigned
; program is exactly the scary dialog we want to avoid on the till.
;
; The shop's own files (dictionary, combos, settings, order history) are NOT
; installed or removed by this: the app keeps them in its own data folder
; outside {app}, so installing, updating and uninstalling never touch them.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Kebbet Zamen"
#define AppExeName "KebzetZamen.exe"

[Setup]
; Never change AppId -- it is what makes a later run an upgrade of this
; install rather than a second copy alongside it.
AppId={{8E5B0A1C-7C3E-4C4B-9E2A-2F7B6D4A91C3}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Kebbet Zamen
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\KebbetZamen
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir=installer_out
OutputBaseFilename=KebzetZamenSetup
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Close the app if it is running, so its files can be replaced. Combined with
; the [Run] entry below, an update from inside the app is: download, swap,
; start again.
CloseApplications=yes
RestartApplications=no

[Files]
; The whole PyInstaller --onedir output: KebzetZamen.exe plus _internal\.
Source: "dist\KebzetZamen\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
; No skipifsilent: a silent install is what the app's own update button runs,
; and it should bring the app back up afterwards.
Filename: "{app}\{#AppExeName}"; Description: "Start {#AppName}"; Flags: nowait postinstall
