; CPCM-Setup.exe – Windows-Installer mit eingebettetem Python 3.12 (64-bit).
; Bauen (aus dem Repo-Root oder von überall): installer/build-setup.sh
; makensis wechselt in dieses Verzeichnis. Die Python-Zip liegt nur unter build/.
Unicode True

!define PRODUCT_NAME "CPCM"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "Andreas Meyer"
!define PRODUCT_EMAIL "ame@sellerbach.de"
!define PRODUCT_WEB "mailto:ame@sellerbach.de"
!define DEFAULT_DIR "D:\AI_Temp\CPCM"

Name "${PRODUCT_NAME}"
Caption "CPCM Setup"
BrandingText "${PRODUCT_PUBLISHER}  ${PRODUCT_EMAIL}"
OutFile "..\CPCM-Setup.exe"
InstallDir "${DEFAULT_DIR}"
InstallDirRegKey HKCU "Software\CPCM" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!define MUI_ICON "..\cpcm.ico"
!define MUI_UNICON "..\cpcm.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "CPCM Setup"
!define MUI_WELCOMEPAGE_TEXT "Dieser Assistent installiert CPCM (Cross Platform Config Manager).$\r$\n$\r$\nAndreas Meyer, ame@sellerbach.de$\r$\n$\r$\nPython 3.12 ist enthalten. Ein separates Python ist nicht nötig.$\r$\n$\r$\nStandardordner: D:\AI_Temp\CPCM. Der Ordner kann geändert werden. Ein vorhandener Ordner vault und die Datei cpcm-settings.json bleiben erhalten."
!define MUI_DIRECTORYPAGE_TEXT_TOP "Zielordner wählen. Voreingestellt ist D:\AI_Temp\CPCM. Der Ordner von ShatuIDE wird abgelehnt. Vorhandene Daten in vault\ und cpcm-settings.json werden nicht gelöscht."
!define MUI_CUSTOMFUNCTION_DIRECTORY_LEAVE RejectShatuDir
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchCPCM
!define MUI_FINISHPAGE_RUN_TEXT "CPCM jetzt starten"
!define MUI_FINISHPAGE_TITLE "CPCM ist installiert"
!define MUI_FINISHPAGE_TEXT "CPCM liegt im gewählten Ordner. Die Verknüpfung auf dem Desktop und im Startmenü startet die mitgelieferte python.exe.$\r$\n$\r$\nAndreas Meyer, ame@sellerbach.de"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "German"

VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "CPCM"
VIAddVersionKey "ProductVersion" "1.0.0"
VIAddVersionKey "FileVersion" "1.0.0"
VIAddVersionKey "FileDescription" "CPCM Setup D:\AI_Temp\CPCM"
VIAddVersionKey "CompanyName" "Andreas Meyer"
VIAddVersionKey "LegalCopyright" "Andreas Meyer"
VIAddVersionKey "Comments" "ame@sellerbach.de"
VIAddVersionKey "InternalName" "CPCM-Setup.exe"
VIAddVersionKey "OriginalFilename" "CPCM-Setup.exe"

!if /FileExists "..\build\python\python.exe"
!else
  !error "build/python/python.exe fehlt. Zuerst installer/build-setup.sh ausführen."
!endif

Function RejectShatuDir
  ${GetFileName} "$INSTDIR" $0
  ${If} $0 == "ShatuIDE"
  ${OrIf} ${FileExists} "$INSTDIR\shatuide.py"
  ${OrIf} ${FileExists} "$INSTDIR\ShatuIDE.exe"
    MessageBox MB_OK|MB_ICONSTOP "Dieser Ordner gehört zu ShatuIDE.$\r$\n$\r$\nCPCM wird nach D:\AI_Temp\CPCM installiert und startet ShatuIDE nicht."
    Abort
  ${EndIf}
FunctionEnd

Function LaunchCPCM
  SetOutPath "$INSTDIR"
  Exec '"$INSTDIR\CPCM.exe"'
FunctionEnd

Section "CPCM" SecMain
  SetShellVarContext current
  SetOutPath "$INSTDIR"

  File "..\cpcm.py"
  File "..\README.md"
  File "..\icon.png"
  File "..\cpcm.ico"
  File "..\Install-CPCM.ps1"
  File "..\Create-Shortcut.ps1"
  File "..\install-cpcm.sh"
  File "..\install-cpcm-bin.sh"
  File "..\CPCM.bat"
  File "..\CPCM.exe"
  File "..\cpcm.sh"
  File "..\CPCM.desktop"
  File "..\pyproject.toml"
  File "..\CPCM.spec"

  SetOutPath "$INSTDIR\cpcm"
  File "..\cpcm\*.py"

  SetOutPath "$INSTDIR\web"
  File "..\web\*.html"
  File "..\web\*.css"
  File "..\web\*.js"

  SetOutPath "$INSTDIR\docs"
  File "..\docs\*.md"

  SetOutPath "$INSTDIR\examples"
  File "..\examples\*.*"

  SetOutPath "$INSTDIR\tests"
  File "..\tests\*.py"

  ; Offizielles Embeddable-Paket. python312._pth macht Installationsverzeichnis und Lib importierbar.
  SetOutPath "$INSTDIR\python"
  File "..\build\python\*.exe"
  File "..\build\python\*.dll"
  File "..\build\python\*.pyd"
  File "..\build\python\*.zip"
  File "..\build\python\*.txt"
  File "..\build\python\*.cat"
  File /oname=python312._pth "python312._pth"
  CreateDirectory "$INSTDIR\python\Lib"

  SetOutPath "$INSTDIR"
  ${If} ${FileExists} "$INSTDIR\vault\*.*"
    DetailPrint "Vorhandener vault bleibt erhalten."
  ${EndIf}
  ${If} ${FileExists} "$INSTDIR\cpcm-settings.json"
    DetailPrint "Vorhandene cpcm-settings.json bleibt erhalten."
  ${EndIf}

  FileOpen $0 "$INSTDIR\AUTOR.txt" w
  FileWrite $0 "CPCM ${PRODUCT_VERSION}$\r$\n"
  FileWrite $0 "${PRODUCT_PUBLISHER}$\r$\n"
  FileWrite $0 "${PRODUCT_EMAIL}$\r$\n"
  FileWrite $0 "Rolle: Windows-Referenz$\r$\n"
  FileWrite $0 "Pfad: $INSTDIR$\r$\n"
  FileClose $0

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\CPCM"
  SetOutPath "$INSTDIR"
  CreateShortCut "$DESKTOP\CPCM.lnk" "$INSTDIR\CPCM.exe" "" "$INSTDIR\cpcm.ico" 0 SW_SHOWNORMAL "" "CPCM - Andreas Meyer, ame@sellerbach.de"
  CreateShortCut "$SMPROGRAMS\CPCM\CPCM.lnk" "$INSTDIR\CPCM.exe" "" "$INSTDIR\cpcm.ico" 0 SW_SHOWNORMAL "" "CPCM - Andreas Meyer, ame@sellerbach.de"
  CreateShortCut "$SMPROGRAMS\CPCM\CPCM deinstallieren.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\cpcm.ico" 0

  WriteRegStr HKCU "Software\CPCM" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "DisplayName" "CPCM"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "DisplayIcon" "$INSTDIR\cpcm.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "HelpLink" "${PRODUCT_WEB}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "URLInfoAbout" "${PRODUCT_WEB}"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM" "EstimatedSize" "$0"
SectionEnd

Section "Uninstall"
  SetShellVarContext current

  Delete "$DESKTOP\CPCM.lnk"
  Delete "$SMPROGRAMS\CPCM\CPCM.lnk"
  Delete "$SMPROGRAMS\CPCM\CPCM deinstallieren.lnk"
  RMDir "$SMPROGRAMS\CPCM"

  ; Programmdateien. vault\ und cpcm-settings.json werden nicht angefasst.
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\cpcm"
  RMDir /r "$INSTDIR\web"
  RMDir /r "$INSTDIR\docs"
  RMDir /r "$INSTDIR\examples"
  RMDir /r "$INSTDIR\tests"
  RMDir /r "$INSTDIR\__pycache__"

  Delete "$INSTDIR\cpcm.py"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\icon.png"
  Delete "$INSTDIR\cpcm.ico"
  Delete "$INSTDIR\Install-CPCM.ps1"
  Delete "$INSTDIR\Create-Shortcut.ps1"
  Delete "$INSTDIR\install-cpcm.sh"
  Delete "$INSTDIR\install-cpcm-bin.sh"
  Delete "$INSTDIR\CPCM.bat"
  Delete "$INSTDIR\CPCM.exe"
  Delete "$INSTDIR\cpcm.sh"
  Delete "$INSTDIR\CPCM.desktop"
  Delete "$INSTDIR\pyproject.toml"
  Delete "$INSTDIR\CPCM.spec"
  Delete "$INSTDIR\AUTOR.txt"
  Delete "$INSTDIR\Uninstall.exe"

  ; Nur entfernen, wenn nichts liegen bleibt (vault, cpcm-settings.json).
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CPCM"
  DeleteRegKey HKCU "Software\CPCM"
SectionEnd
