# InstantLens Doc — About

## 2.6.27

Polish / installer in sync flow.

| | |
|---|---|
| Product | InstantLens Doc |
| Version | **2.6.27** |
| Vendor | Andreas Meyer |
| Contact | ame@sellerbach.de |

New in 2.6.27: `sync-ild.ps1 -BuildInstaller` (optional Setup.exe after sync); post-sync steps for `install-ild.ps1` + keygen + scripting; robust mouse-wheel scroll for text/Word Suite; help/info + i18n keys.

After sync:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
```

## 2.6.26

Polish / installer consolidation. Hardened Windows installer (VERSION.txt→ISCC, preflight, CustomMessages DE/EN).

## 2.6.25

Stylus / palm rejection, document outline pane, script/plugin hooks, opt-in local telemetry, 3D limited viewer, Inno installer.

## 2.6.24

Hyperlinks, graphics/media (scale/crop/shapes/video URL), EPUB export.

## 2.6.23

Shared review / cloud-folder collaboration (folder sync + optional endpoint).

## 2.6.22

Batch processing, digital signatures (eIDAS), mail-merge polish.
