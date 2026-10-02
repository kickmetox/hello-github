; Inno Setup — InstantLens Doc
; Voraussetzung: Inno Setup 6 (iscc.exe im PATH oder ISCC_PATH setzen)
;
; Build-Varianten:
;   A) Python-Portable-Layout (empfohlen für Dev):
;      SourceRoot = Ordner mit run.bat, instantlensdoc\, assets\, …
;      ISCC mit /DSourceRoot=...\InstantLensDoc /DUsePythonLauncher=1
;   B) Gebündelte EXE (PyInstaller):
;      SourceRoot = dist\InstantLensDoc mit InstantLensDoc.exe
;
; Startmenü: Gruppe „InstantLens Doc“ mit App + Keygen + Hilfe-Link
; Desktop: Task „Desktop-Verknüpfung“ (Standard: aktiv)
;
; Siehe: build-installer.ps1

#define MyAppName "InstantLens Doc"
#define MyAppVersion "0.1.7"
#define MyAppPublisher "Andreas Meyer"
#define MyAppURL "mailto:ame@sellerbach.de"
#ifndef SourceRoot
  #define SourceRoot "..\dist\InstantLensDoc"
#endif
#ifndef UsePythonLauncher
  #define UsePythonLauncher "0"
#endif

[Setup]
AppId={{A8E3C2F1-ILD0-4B2A-9E01-INSTANTLENSDOC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\InstantLensDoc
DefaultGroupName={#MyAppName}
; Startmenü-Gruppe sichtbar lassen (Icons unten)
DisableProgramGroupPage=no
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=InstantLensDoc-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\assets\app.ico
LicenseFile=
InfoBeforeFile=
InfoAfterFile=installer-hinweis.txt
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop-Verknüpfung standardmäßig aktiv — abwählbar
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Verknüpfungen:"; Flags: checkedonce
Name: "startmenu"; Description: "Einträge im Startmenü belassen"; GroupDescription: "Verknüpfungen:"; Flags: checkedonce

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Hinweisdatei immer mitliefern (auch wenn SourceRoot kein INFO hat)
Source: "installer-hinweis.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
#if UsePythonLauncher == "1"
Name: "{group}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc starten"; Tasks: startmenu
Name: "{group}\Keygenerator"; Filename: "{app}\run-keygen.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "Lizenz-Key erzeugen"; Tasks: startmenu
Name: "{group}\INFO lesen"; Filename: "{app}\INFO.md"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc"; Tasks: desktopicon
#else
Name: "{group}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc starten"; Tasks: startmenu
Name: "{group}\Keygenerator"; Filename: "{app}\InstantLensDoc.exe"; Parameters: "-m keygen --gui"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "Lizenz-Key erzeugen"; Tasks: startmenu
Name: "{group}\INFO lesen"; Filename: "{app}\INFO.md"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc"; Tasks: desktopicon
#endif

[Run]
#if UsePythonLauncher == "1"
Filename: "{app}\run.bat"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent
#else
Filename: "{app}\InstantLensDoc.exe"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent
#endif

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
