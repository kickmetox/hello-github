# CPCM unter Linux bauen

Andreas Meyer  
ame@sellerbach.de

Dieser Ablauf erzeugt auf einem Linux-Rechner das Windows-Programm `CPCM.exe` und den Installer `CPCM-Setup.exe`. Das Fenster selbst ist ein Windows-Programm und läuft nicht unter Linux. Unter Linux prüft `python3 cpcm.py window` nur, dass der Befehl vorhanden ist, und verweist auf diese Anleitung.

## Pakete

Debian oder Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3 gcc-mingw-w64-x86-64 nsis curl unzip p7zip-full
```

Python 3.11 oder neuer. Weitere Python-Pakete braucht der Bau nicht. MinGW übersetzt `installer/cpcm_launch_win.c` nach `CPCM.exe`. NSIS packt `CPCM-Setup.exe`.

## Bauen

Im Quellordner:

```bash
bash installer/build-setup.sh
```

Das Skript lädt das offizielle Python-3.12.10-Embeddable-Paket (64-bit) nach `build/cache/`, entpackt es nach `build/python/` und schreibt `python312._pth`. Danach entstehen:

- `CPCM.exe`, der Windows-Starter. Er ruft `python\pythonw.exe cpcm.py window` auf. Kein Browser, keine `.py`-Dateizuordnung.
- `CPCM-Setup.exe`, der Installer. Zielordner voreingestellt `D:\AI_Temp\CPCM`.

`build/` bleibt lokal und gehört nicht ins Archiv der Quellen, das der Installer selbst enthält das Python.

## Prüfen

```bash
python3 -m unittest discover -s tests -p 'test_cpcm_*.py'
python3 cpcm.py window
file CPCM.exe CPCM-Setup.exe
```

`window` unter Linux gibt den Hinweis auf diese Anleitung aus und öffnet kein Fenster. `file` meldet für `CPCM.exe` ein PE32+-Programm und für `CPCM-Setup.exe` einen Nullsoft-Installer.

## Windows-Programm aus dem Bau

`CPCM-Setup.exe` auf den Windows-Rechner kopieren und starten. Das Desktop-Symbol öffnet das Fenster. Die Bedienungsanleitung ist `docs/BEDIENUNGSANLEITUNG.rtf`, die Feature-Liste `docs/FEATURE-LISTE.rtf`, die Hilfe im Menü Hilfe.
