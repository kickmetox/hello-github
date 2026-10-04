# InstantLens Doc — Hilfe

## 2.6.27

Version **2.6.27** — Polish / Installer im Sync-Flow.

**Sync + Shortcuts + optional Setup.exe:**

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1" -SkipStart
cd D:\AI_Temp\InstantLensDoc
powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
```

Oder Sync mit Installer-Build: `sync-ild.ps1 -BuildInstaller -SkipStart` (braucht Inno Setup 6 / ISCC).

**Keygen:** `run-keygen.bat` · `python -m keygen kunde@example.com` · `--verify "ILD1...."`.

**Scripting:** `python -m ild --help` · `run-ild.bat` · `.\scripts\ild.ps1` · Store `instantlensdoc-scripting.md`.

**Mausrad (Text/Word-Suite):** Trackpad/`pixelDelta` + Mausrad; Shift+Rad → horizontal; Scroll auch über Zeilennummern/Minimap und Markdown-Vorschau.

Ergebnis Setup: `dist\InstantLensDoc-Setup-2.6.27.exe` (Startmenü, optional Desktop, Uninstall, 64-Bit).

## 2.6.26

Polish / Installer-Konsolidierung. Einzeiler: `.\scripts\build-windows-installer.ps1` → `InstantLensDoc-Setup-2.6.26.exe`.

## 2.6.25

Stylus / Dokumentstruktur / Hooks / Telemetrie / 3D Limited Viewer.

## 2.6.23

Bearbeiten → Review → **Gemeinsames Review…**: Session starten oder beitreten (Freigabeordner / optional Endpoint).
Einschränkungen: kein gehosteter Cloud-Dienst, kein CRDT; Offline bleibt nutzbar.
