# Contributing — InstantLens Doc

Kurzleitfaden für lokale Entwicklung und Smoke-Checks.

## Voraussetzungen

- Python ≥ 3.10
- Abhängigkeiten: `pip install -r requirements.txt`
- GUI-Tests: PySide6 (Headless: `QT_QPA_PLATFORM=offscreen`)

## Nightly-Smoke (`smoke_ild`)

Leichtgewichtiger CI-/Nightly-Check (Version, Imports, CLI, Measure/Diff/Import, Changelog):

```bat
python scripts\smoke_ild.py
python scripts\smoke_ild.py --qt
python scripts\smoke_ild.py --json
```

Smoke-Beispielkommando (JSON-Summary, Exit 0 = OK):

```bat
python scripts\smoke_ild.py --json
```

| Exit | Bedeutung |
|------|-----------|
| 0 | OK (`ok=true`) |
| 1 | Fehler (`ok=false`) |
| 2 | ungültige Option (`--help` → 0) |

`--json` liefert `ok`, `checks`, `duration_ms`, `version`. Bei Fail enthält `checks[]` ein Objekt mit `error` (max 200 Zeichen, Overflow `…`).

Vollständiger Smoke (inkl. Qt-UI-Pfad):

```bat
set QT_QPA_PLATFORM=offscreen
python scripts\smoke_test.py
```

## GitHub Actions Stub

Unter `.github/workflows/smoke-ild.yml` liegt ein **Workflow-Stub (manual only)**. Nur `workflow_dispatch` — kein Push/PR-Trigger, keine Cloud-CI-Pflicht. Lokal: `python scripts/smoke_ild.py`.

## Sync (Windows)

**Sync-Einzeiler** = Pfad zu `sync-ild.ps1` (Repo: `scripts/sync-ild.ps1`, lokal typisch `D:\AI_Temp\sync-ild.ps1`):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

Siehe `INFO.md` / `scripts/sync-ild.ps1`.
