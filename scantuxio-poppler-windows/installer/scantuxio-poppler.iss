; Inno Setup 6 — ScanTuxio + gebündeltes Poppler (Windows)
; Voraussetzung: App-Dateien und vendor\poppler\... im Source-Tree
; Build: ISCC.exe scantuxio-poppler.iss
;
; Poppler-Binaries = GPL (Hinweis im Setup und LICENSE-POPPLER.txt mitliefern)

#define MyAppName "ScanTuxio"
#define MyAppVersion "0.0.0"
#define MyAppPublisher "ScanTuxio"
#define MyAppExeName "ScanTuxio.exe"
; SourceRoot = Ordner mit ScanTuxio.exe (Build-Artefakte)
#define SourceRoot "..\..\ScanTuxio Win"
; Poppler nach download-poppler.ps1
#define PopplerRoot "..\vendor\poppler"

[Setup]
AppId={{A7C3E9D1-5B24-4F0A-9C31-SCANTUXIO01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=ScanTuxio-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\docs\LICENSE-THIRD-PARTY.txt
InfoBeforeFile=..\docs\INSTALL-POPPLER-NOTICE.txt
PrivilegesRequired=admin

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Hauptprogramm (frozen) — Pfade an lokalen Build anpassen
Source: "{#SourceRoot}\ScanTuxio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\*.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\scantuxio_entry.py"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\FEATURES.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Launcher mit Poppler-PATH
Source: "..\run\run.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\run\run.ps1"; DestDir: "{app}"; Flags: ignoreversion
; Poppler-Finder (für Dev-Entry / künftige Builds)
Source: "..\python\poppler_paths.py"; DestDir: "{app}\python"; Flags: ignoreversion
; Poppler-Bundle (GPL) — gesamter vendor\poppler Baum
Source: "{#PopplerRoot}\*"; DestDir: "{app}\vendor\poppler"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\LICENSE-THIRD-PARTY.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\INSTALL-POPPLER-NOTICE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\run.bat"
Name: "{group}\{#MyAppName} (EXE)"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run.bat"; Tasks: desktopicon

[Run]
Filename: "{app}\run.bat"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not FileExists(ExpandConstant('{#PopplerRoot}\Library\bin\pdftoppm.exe')) then
  begin
    if not FileExists(ExpandConstant('{#PopplerRoot}\bin\pdftoppm.exe')) then
      MsgBox('Warnung: pdftoppm.exe unter PopplerRoot nicht gefunden. Bitte zuerst scripts\download-poppler.ps1 ausführen.', mbError, MB_OK);
  end;
end;
