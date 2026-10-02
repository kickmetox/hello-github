# InstantLens Doc — Keygenerator

Separates Tool zur Erzeugung und Prüfung von Lizenzkeys.

## Windows (schnell)

```bat
run-keygen.bat
```

Startet die GUI. Keys gelten **32 Tage (30+2)**. Kontakt: **ame@sellerbach.de**.

## CLI

```bash
# Erzeugen
python -m keygen kunde@example.com

# Prüfen
python -m keygen --verify "ILD1...."

# GUI
python -m keygen --gui
```

Format: `ILD1.<payload>.<sig>`.
