; Inno Setup Vorlage — InstantLens Doc
; SourceRoot auf den Build-Output anpassen. Kein Poppler im Setup.

#define MyAppName "InstantLens Doc"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Andreas Meyer"
#define MyAppURL "mailto:ame@sellerbach.de"
#ifndef SourceRoot
  #define SourceRoot "..\dist\InstantLensDoc"
#endif

[Setup]
AppId={{A8E3C2F1-ILD0-4B2A-9E01-INSTANTLENSDOC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\InstantLensDoc
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=InstantLensDoc-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\app.ico

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\InstantLensDoc.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung"; GroupDescription: "Zusätzlich:"

[Run]
Filename: "{app}\InstantLensDoc.exe"; Description: "{#MyAppName} starten"; Flags: nowait postinstall skipifsilent
