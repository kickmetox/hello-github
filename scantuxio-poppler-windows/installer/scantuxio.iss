; Inno Setup 6 — ScanTuxio Windows (lizenzfreundlich, OHNE Poppler/GPL)
; PDF über pypdfium2/PDFium — bereits in ScanTuxio.exe bzw. _internal/ nach PyInstaller
;
; Voraussetzung:
;   1) App mit pypdfium2 gebaut: pyinstaller ... --collect-all pypdfium2
;   2) SourceRoot zeigt auf den Frozen-Output (ScanTuxio.exe + Begleitdateien)
;
; Build: ISCC.exe scantuxio.iss

#define MyAppName "ScanTuxio"
#define MyAppVersion "0.0.0"
#define MyAppPublisher "ScanTuxio"
#define MyAppExeName "ScanTuxio.exe"
; Ordner mit ScanTuxio.exe (Build-Artefakte / dist)
#define SourceRoot "..\..\ScanTuxio Win"

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
InfoBeforeFile=..\docs\INSTALL-NOTICE.txt
PrivilegesRequired=admin

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Frozen App — gesamte Distribution (exe, pyd, dll, _internal, …)
; Wenn PyInstaller onedir: SourceRoot = dist\ScanTuxio\
Source: "{#SourceRoot}\ScanTuxio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\*.pyd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\*.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
; Dev-/Doku-Dateien optional
Source: "{#SourceRoot}\scantuxio_entry.py"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\FEATURES.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Launcher + PDF-Hilfsmodul (für Dev-Entry / Diagnose)
Source: "..\run\run.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\run\run.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\python\pdf_render.py"; DestDir: "{app}\python"; Flags: ignoreversion
Source: "..\python\poppler_paths.py"; DestDir: "{app}\python"; Flags: ignoreversion
; Lizenzhinweise (kein Poppler-Bundle)
Source: "..\docs\LICENSE-THIRD-PARTY.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\INSTALL-NOTICE.txt"; DestDir: "{app}"; Flags: ignoreversion
; Explizit KEIN vendor\poppler\* — GPL-Binaries werden nicht mitgeliefert

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
  if not FileExists(ExpandConstant('{#SourceRoot}\{#MyAppExeName}')) then
    MsgBox('ScanTuxio.exe unter SourceRoot nicht gefunden. SourceRoot in scantuxio.iss anpassen und App zuvor mit pypdfium2 bauen.', mbError, MB_OK);
end;
