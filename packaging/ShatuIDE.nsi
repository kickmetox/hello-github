Unicode True
ManifestDPIAware true

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"

!ifndef STAGE
  !error "STAGE fehlt. Aufruf: makensis -DSTAGE=... -DOUT=... -DVERSION=1.0.0.0 -DVERSIONTEXT=1.0.0 -DICON=..."
!endif
!ifndef OUT
  !error "OUT fehlt."
!endif
!ifndef ICON
  !error "ICON fehlt."
!endif
!ifndef VERSION
  !define VERSION "1.0.0.0"
!endif
!ifndef VERSIONTEXT
  !define VERSIONTEXT "${VERSION}"
!endif

Name "ShatuIDE"
OutFile "${OUT}/ShatuIDE-Setup.exe"
InstallDir "$PROGRAMFILES64\ShatuIDE"
InstallDirRegKey HKLM "Software\ShatuIDE" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "ShatuIDE"
AutoCloseWindow true
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${VERSION}"
VIAddVersionKey /LANG=1031 "ProductName" "ShatuIDE"
VIAddVersionKey /LANG=1031 "FileDescription" "ShatuIDE-Einrichtung"
VIAddVersionKey /LANG=1031 "CompanyName" "Andreas Meyer"
VIAddVersionKey /LANG=1031 "LegalCopyright" "Andreas Meyer"
VIAddVersionKey /LANG=1031 "FileVersion" "${VERSIONTEXT}"

!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING
!define MUI_ABORTWARNING_TEXT "Die Einrichtung von ShatuIDE wird abgebrochen. Es wird nichts geändert."
!define MUI_ABORTWARNING_CANCEL_DEFAULT

!define MUI_WELCOMEPAGE_TITLE "Willkommen beim ShatuIDE-Setup"
!define MUI_WELCOMEPAGE_TEXT "Dieser Assistent richtet ShatuIDE ein.$\r$\n$\r$\nDie nächsten Seiten wählen Zielordner und Startmenü. Installieren kopiert danach die Dateien und zeigt den Fortschritt.$\r$\n$\r$\nEs entstehen ein Desktop-Symbol und ein Startmenü-Eintrag.$\r$\n$\r$\nPython 3 muss vorhanden sein. Dieses Paket bringt kein Python mit."

!define MUI_DIRECTORYPAGE_TEXT_TOP "ShatuIDE wird in den folgenden Ordner installiert. Durchsuchen wählt einen anderen Ordner. Weiter geht zum Startmenü."
!define MUI_DIRECTORYPAGE_TEXT_DESTINATION "Zielordner"

!define MUI_STARTMENUPAGE_DEFAULTFOLDER "ShatuIDE"
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\ShatuIDE"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "StartMenuFolder"

!define MUI_FINISHPAGE_TITLE "ShatuIDE ist eingerichtet"
!define MUI_FINISHPAGE_TEXT "ShatuIDE ist eingerichtet.$\r$\n$\r$\nStart über das Desktop-Symbol, das Startmenü oder das Kästchen unten.$\r$\n$\r$\nDie Dateien liegen im gewählten Ordner. Python 3 wird zum Start gebraucht.$\r$\n$\r$\nFertigstellen schließt den Assistenten."
!define MUI_FINISHPAGE_RUN "$INSTDIR\ShatuIDE.exe"
!define MUI_FINISHPAGE_RUN_TEXT "ShatuIDE jetzt starten"
!define MUI_FINISHPAGE_NOAUTOCLOSE

!define MUI_UNCONFIRMPAGE_TEXT_TOP "ShatuIDE wird entfernt. Desktop-Symbol, Startmenü-Eintrag und der Programmordner werden gelöscht."

Var StartMenuFolder
Var ReadyDialog

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
PageEx custom
  PageCallbacks ReadyCreate ReadyLeave
  Caption "ShatuIDE"
PageExEnd
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "German"

!insertmacro GetSize

Function .onInit
  SetRegView 64
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "ShatuIDE braucht Windows 64-bit."
    Abort
  ${EndIf}
FunctionEnd

Function un.onInit
  SetRegView 64
FunctionEnd

Function ReadyCreate
  !insertmacro MUI_HEADER_TEXT "Bereit zur Installation" "Prüfen Sie die Angaben. Installieren kopiert die Dateien."
  nsDialogs::Create 1018
  Pop $ReadyDialog
  ${If} $ReadyDialog == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0 0 100% 120u "ShatuIDE wird in diesen Ordner kopiert:$\r$\n$\r$\n$INSTDIR$\r$\n$\r$\nDanach gibt es ein Symbol auf dem Desktop und einen Eintrag im Startmenü.$\r$\n$\r$\nPython 3 muss vorhanden sein. Dieses Paket bringt kein Python mit.$\r$\n$\r$\nInstallieren startet das Kopieren. Zurück ändert den Ordner. Abbrechen ändert nichts."
  Pop $0
  GetDlgItem $0 $HWNDPARENT 1
  SendMessage $0 ${WM_SETTEXT} 0 "STR:Installieren"
  nsDialogs::Show
FunctionEnd

Function ReadyLeave
  GetDlgItem $0 $HWNDPARENT 1
  SendMessage $0 ${WM_SETTEXT} 0 "STR:$(^NextBtn)"
FunctionEnd

Section "ShatuIDE" SecApp
  SetOutPath "$INSTDIR"
  File /r /x ausgabe /x __pycache__ /x *.pyc "${STAGE}/*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\ShatuIDE.lnk" "$INSTDIR\ShatuIDE.exe" "" "$INSTDIR\ShatuIDE.exe" 0
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\ShatuIDE.lnk" "$INSTDIR\ShatuIDE.exe" "" "$INSTDIR\ShatuIDE.exe" 0
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Deinstallieren.lnk" "$INSTDIR\Uninstall.exe"
  !insertmacro MUI_STARTMENU_WRITE_END
  WriteRegStr HKLM "Software\ShatuIDE" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "DisplayName" "ShatuIDE"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "DisplayIcon" "$INSTDIR\ShatuIDE.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "Publisher" "Andreas Meyer"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "DisplayVersion" "${VERSIONTEXT}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE" "EstimatedSize" $0
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\ShatuIDE.lnk"
  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
  Delete "$SMPROGRAMS\$StartMenuFolder\ShatuIDE.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Deinstallieren.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShatuIDE"
  DeleteRegKey HKLM "Software\ShatuIDE"
SectionEnd
