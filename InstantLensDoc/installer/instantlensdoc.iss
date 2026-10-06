; Inno Setup - InstantLens Doc 2.6.56
; Voraussetzung: Inno Setup 6 (iscc.exe im PATH oder ISCC_PATH / -IsccPath)
;
; Build-Varianten:
;   A) Python-Portable-Layout (Dev):
;      SourceRoot = Ordner mit run.bat, instantlensdoc\, assets\, ...
;      ISCC mit /DSourceRoot=...\InstantLensDoc /DUsePythonLauncher=1
;      Keygen-Shortcut -> {app}\run-keygen.bat
;   B) Gebuendelte EXE (PyInstaller) - empfohlen nach build-windows.ps1:
;      SourceRoot = dist\InstantLensDoc mit InstantLensDoc.exe
;      Keygen-EXE-Pfad: {app}\InstantLensKeygen.exe
;      (build-windows.ps1 kopiert Keygen dorthin; build-installer.ps1 ebenfalls)
;
; Optionen:
;   /DMyAppVersion=x.y.z  - Version ueberschreiben (Default unten; build-*.ps1 setzt aus VERSION.txt)
;   /DIncludeKeygen=1     - Keygen mitpacken (run-keygen.bat bzw. InstantLensKeygen.exe)
;   /DIncludeKeygen=0     - ohne Keygen-Shortcuts/Dateien
;
; Desktop: Task "Desktop-Verknuepfung erstellen" - optional Checkbox (Flags: checkedonce,
;   Standard beim ersten Install aktiv; Nutzer kann abwaehlen). Shortcuts nur bei Tasks: desktopicon.
; Uninstaller: Startmenue + Systemsteuerung (UninstallDisplay*)
;
; Siehe: build-installer.ps1  /  scripts\build-windows-installer.ps1

#define MyAppName "InstantLens Doc"
#ifndef MyAppVersion
  #define MyAppVersion "2.6.56"
#endif
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
AppMutex=InstantLensDoc_Setup_Mutex
DefaultDirName={autopf}\InstantLensDoc
DefaultGroupName={#MyAppName}
; Startmenue-Gruppe sichtbar lassen (Icons unten)
DisableProgramGroupPage=no
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=InstantLensDoc-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=6.1sp1
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
UsePreviousTasks=yes
DisableWelcomePage=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
german.TaskDesktopIcon=Desktop-Verknuepfung erstellen
german.TaskStartMenu=Eintraege im Startmenue belassen
german.TaskGroup=Verknuepfungen:
german.LaunchAfterInstall={#MyAppName} jetzt starten
german.IconAppComment=InstantLens Doc starten
german.IconKeygenComment=Lizenz-Key erzeugen
german.IconUninstallComment=InstantLens Doc entfernen
english.TaskDesktopIcon=Create a desktop shortcut
english.TaskStartMenu=Keep Start Menu entries
english.TaskGroup=Additional icons:
english.LaunchAfterInstall=Launch {#MyAppName} now
english.IconAppComment=Start InstantLens Doc
english.IconKeygenComment=Generate license key
english.IconUninstallComment=Remove InstantLens Doc

[Tasks]
; Desktop-Verknuepfung standardmaessig aktiv - abwaehlbar
Name: "desktopicon"; Description: "{cm:TaskDesktopIcon}"; GroupDescription: "{cm:TaskGroup}"; Flags: checkedonce
Name: "startmenu"; Description: "{cm:TaskStartMenu}"; GroupDescription: "{cm:TaskGroup}"; Flags: checkedonce

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Hinweisdatei immer mitliefern (auch wenn SourceRoot kein INFO hat)
Source: "installer-hinweis.txt"; DestDir: "{app}"; Flags: ignoreversion
; Icon fuer Uninstaller/Shortcuts absichern (falls SourceRoot kein assets hat)
Source: "..\assets\app.ico"; DestDir: "{app}\assets"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
#if UsePythonLauncher == "1"
Name: "{group}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "{cm:IconAppComment}"; Tasks: startmenu
#if IncludeKeygen == "1"
Name: "{group}\Keygenerator"; Filename: "{app}\run-keygen.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "{cm:IconKeygenComment}"; Tasks: startmenu
#endif
Name: "{group}\INFO lesen"; Filename: "{app}\INFO.md"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"; IconFilename: "{app}\assets\app.ico"; Comment: "{cm:IconUninstallComment}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "{#MyAppName}"; Tasks: desktopicon
#else
Name: "{group}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "{cm:IconAppComment}"; Tasks: startmenu
#if IncludeKeygen == "1"
Name: "{group}\Keygenerator"; Filename: "{app}\InstantLensKeygen.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "{cm:IconKeygenComment}"; Tasks: startmenu
#endif
Name: "{group}\INFO lesen"; Filename: "{app}\INFO.md"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"; IconFilename: "{app}\assets\app.ico"; Comment: "{cm:IconUninstallComment}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app.ico"; Comment: "{#MyAppName}"; Tasks: desktopicon
#endif

[Run]
#if UsePythonLauncher == "1"
; run.bat is ASCII-safe as of 2.6.52; still prefer nowait + skipifsilent
Filename: "{app}\run.bat"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent
#else
Filename: "{app}\InstantLensDoc.exe"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent
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
