# InstantLens Doc — Hilfe

## 2.6.26

Version **2.6.26** — Polish / Installer-Konsolidierung.

Windows-Installer (Setup.exe) auf Windows x64 mit Inno Setup 6:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
```

Ergebnis: `dist\InstantLensDoc-Setup-2.6.26.exe` (Startmenü, optional Desktop, Uninstall, 64-Bit).

## 2.6.25

Stylus / Dokumentstruktur / Hooks / Telemetrie / 3D Limited Viewer.

## 2.6.23

Bearbeiten → Review → **Gemeinsames Review…**: Session starten oder beitreten (Freigabeordner / optional Endpoint).
Einschränkungen: kein gehosteter Cloud-Dienst, kein CRDT; Offline bleibt nutzbar.
