# InstantLens Doc — Help

## 2.6.28

Version **2.6.28** — polish / installer in sync flow.

**Sync + shortcuts + optional Setup.exe:**

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1" -SkipStart
cd D:\AI_Temp\InstantLensDoc
powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
```

Or sync with installer build: `sync-ild.ps1 -BuildInstaller -SkipStart` (needs Inno Setup 6 / ISCC).

**Keygen:** `run-keygen.bat` · `python -m keygen user@example.com` · `--verify "ILD1...."`.

**Scripting:** `python -m ild --help` · `run-ild.bat` · `.\scripts\ild.ps1`.

**Mouse wheel (text/Word Suite):** trackpad/`pixelDelta` + wheel; Shift+wheel → horizontal; also over line numbers/minimap and Markdown preview.

Result: `dist\InstantLensDoc-Setup-2.6.28.exe` (Start Menu, optional desktop, uninstall, 64-bit).

## 2.6.26

Polish / installer consolidation. One-liner: `.\scripts\build-windows-installer.ps1` → `InstantLensDoc-Setup-2.6.26.exe`.

## 2.6.25

Stylus / document outline / hooks / telemetry / 3D limited viewer.

## 2.6.23

Edit → Review → **Shared review…**: start or join a session (shared folder / optional endpoint).
Limitations: no hosted cloud service, no CRDT; offline remains usable.
