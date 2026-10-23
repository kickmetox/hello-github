; Flare-Installer für Windows 11 x64. Bauen mit makensis, auch unter Linux.
Unicode true
ManifestDPIAware true
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"

!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef PAYLOAD
  !error "PAYLOAD fehlt. Beispiel: makensis -DPAYLOAD=/pfad/dist/Flare flare.nsi"
!endif
!ifndef OUTFILE
  !error "OUTFILE fehlt."
!endif

!define APPNAME "Flare"
!define EXE "Flare.exe"

Name "${APPNAME} ${VERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\Flare"
InstallDirRegKey HKCU "Software\Flare" "InstallDir"
RequestExecutionLevel user
ShowInstDetails show
ShowUninstDetails show
BrandingText "Flare ${VERSION}"

!define MUI_ABORTWARNING
!define MUI_ICON "${__FILEDIR__}\flare.ico"
!define MUI_UNICON "${__FILEDIR__}\flare.ico"
!define MUI_WELCOMEPAGE_TITLE "Flare einrichten"
!define MUI_WELCOMEPAGE_TEXT "Flare sucht Programme, Ordner und Dateien.$\r$\n$\r$\nNach der Einrichtung liegt es im Startmenü. Mit der Option unten startet es bei der Anmeldung und öffnet sich mit Strg+Alt+Leertaste aus anderen Programmen."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Flare jetzt starten"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "German"

VIProductVersion "${VERSION}.0"
VIFileVersion "${VERSION}.0"
VIAddVersionKey /LANG=1031 "ProductName" "Flare"
VIAddVersionKey /LANG=1031 "FileDescription" "Flare Setup für Windows"
VIAddVersionKey /LANG=1031 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1031 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=1031 "CompanyName" "Flare"
VIAddVersionKey /LANG=1031 "LegalCopyright" "Flare"

Section "Flare" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\Flare" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "DisplayName" "Flare"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "Publisher" "Flare"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare" "EstimatedSize" "$0"

  CreateDirectory "$SMPROGRAMS"
  SetOutPath "$INSTDIR"
  CreateShortcut "$SMPROGRAMS\Flare.lnk" "$INSTDIR\${EXE}" "" "$INSTDIR\${EXE}" 0
SectionEnd

Section "Mit Windows starten" SecAuto
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Flare" "$\"$INSTDIR\${EXE}$\" --background"
SectionEnd

LangString DESC_Main ${LANG_GERMAN} "Programm, Suche und Startmenü-Eintrag. Der Katalog bleibt unter %LOCALAPPDATA%\Flare erhalten."
LangString DESC_Auto ${LANG_GERMAN} "Startet Flare bei der Anmeldung im Hintergrund. Strg+Alt+Leertaste öffnet die Suche."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_Main)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecAuto} $(DESC_Auto)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Flare"
  Delete "$SMPROGRAMS\Flare.lnk"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Flare"
  DeleteRegKey HKCU "Software\Flare"
SectionEnd

Function .onInit
  ${IfNot} ${RunningX64}
    ${IfNot} ${IsNativeARM64}
      MessageBox MB_ICONSTOP "Flare braucht 64-Bit-Windows (Windows 11)."
      Abort
    ${EndIf}
  ${EndIf}
FunctionEnd
