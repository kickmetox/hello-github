# InstantLens Doc — Help

## 2.6.26

Version **2.6.26** — polish / installer consolidation.

Windows installer (Setup.exe) on Windows x64 with Inno Setup 6:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
```

Result: `dist\InstantLensDoc-Setup-2.6.26.exe` (Start Menu, optional desktop, uninstall, 64-bit).

## 2.6.25

Stylus / document outline / hooks / telemetry / 3D limited viewer.

## 2.6.23

Edit → Review → **Shared review…**: start or join a session (shared folder / optional endpoint).
Limitations: no hosted cloud service, no CRDT; offline remains usable.
