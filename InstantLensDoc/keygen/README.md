# InstantLens Doc — Keygenerator

Separates Tool zur Erzeugung und Prüfung von Lizenzkeys.

```bash
# CLI
python -m keygen kunde@example.com

# Prüfen
python -m keygen --verify "ILD1...."

# GUI
python -m keygen --gui
```

Keys: Format `ILD1.<payload>.<sig>`, Laufzeit **32 Tage (30+2)** ab Ausstellung.  
Neue Keys: Mail an **ame@sellerbach.de**.

Windows:

```bat
python -m keygen --gui
```
