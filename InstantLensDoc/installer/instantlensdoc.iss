; Inno Setup — InstantLens Doc 2.6.6
; Voraussetzung: Inno Setup 6 (iscc.exe im PATH oder ISCC_PATH setzen)
;
; Build-Varianten:
;   A) Python-Portable-Layout (empfohlen für Dev):
;      SourceRoot = Ordner mit run.bat, instantlensdoc\, assets\, …
;      ISCC mit /DSourceRoot=...\InstantLensDoc /DUsePythonLauncher=1
;      Keygen-Shortcut → {app}\run-keygen.bat
;   B) Gebündelte EXE (PyInstaller):
;      SourceRoot = dist\InstantLensDoc mit InstantLensDoc.exe
;      Keygen-EXE-Pfad: {app}\InstantLensKeygen.exe
;      (build-windows.ps1 kopiert Keygen dorthin; build-installer.ps1 ebenfalls)
;
; Optionen:
;   /DIncludeKeygen=1  — Keygen mitpacken (run-keygen.bat bzw. InstantLensKeygen.exe)
;   /DIncludeKeygen=0  — ohne Keygen-Shortcuts/Dateien
;
; Desktop: Task „Desktop-Verknüpfung erstellen“ — optional Checkbox (Flags: checkedonce,
;   Standard beim ersten Install aktiv; Nutzer kann abwählen). Shortcuts nur bei Tasks: desktopicon.
; Uninstaller: Startmenü + Systemsteuerung (UninstallDisplay*)
;
; Siehe: build-installer.ps1

#define MyAppName "InstantLens Doc"
#define MyAppVersion "2.6.6"
#define MyAppPublisher "Andreas Meyer"
#define MyAppURL "mailto:ame@sellerbach.de"
#ifndef SourceRoot
  #define SourceRoot "..\dist\InstantLensDoc"
#endif
#ifndef UsePythonLauncher
  #define UsePythonLauncher "0"
#endif
#ifndef IncludeKeygen
  #define IncludeKeygen "1"
#endif

[Setup]
AppId={{A8E3C2F1-ILD0-4B2A-9E01-INSTANTLENSDOC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
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
Uninstallable=yes
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\assets\app.ico
LicenseFile=
InfoBeforeFile=
InfoAfterFile=installer-hinweis.txt
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoDescription={#MyAppName} Setup
CloseApplications=yes
RestartApplications=no

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
; Icon für Uninstaller/Shortcuts absichern (falls SourceRoot kein assets hat)
Source: "..\assets\app.ico"; DestDir: "{app}\assets"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
#if UsePythonLauncher == "1"
Name: "{group}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc starten"; Tasks: startmenu
#if IncludeKeygen == "1"
Name: "{group}\Keygenerator"; Filename: "{app}\run-keygen.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "Lizenz-Key erzeugen"; Tasks: startmenu
#endif
Name: "{group}\INFO lesen"; Filename: "{app}\INFO.md"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc entfernen"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc"; Tasks: desktopicon
#else
Name: "{group}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc starten"; Tasks: startmenu
#if IncludeKeygen == "1"
Name: "{group}\Keygenerator"; Filename: "{app}\InstantLensKeygen.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "Lizenz-Key erzeugen"; Tasks: startmenu
#endif
Name: "{group}\INFO lesen"; Filename: "{app}\INFO.md"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc entfernen"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "InstantLens Doc"; Tasks: desktopicon
#endif

[Run]
#if UsePythonLauncher == "1"
Filename: "{app}\run.bat"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent
#else
Filename: "{app}\InstantLensDoc.exe"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent
#endif

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\instantlensdoc\__pycache__"
Type: filesandordirs; Name: "{app}\ild_pdf\__pycache__"
Type: files; Name: "{app}\.smoke_license.json"
Type: files; Name: "{app}\.smoke_export.html"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
