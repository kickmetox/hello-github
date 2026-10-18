# Linux-Fassung aus der fertigen Windows-Fassung erstellen

Andreas Meyer  
ame@sellerbach.de

Diese Anleitung gilt erst nach der fertigen Windows-Fassung in `D:\AI_Temp\CPCM`. Es wird nichts neu programmiert. Dieselben Dateien werden unter Linux an einen festen Ort gelegt und gestartet.

Zielordner: `/home/<benutzer>/AI_Temp/CPCM`  
Beispiel: `/home/andreas/AI_Temp/CPCM`

## 1. Voraussetzung prüfen

Auf dem Windows-Rechner müssen existieren:

- `D:\AI_Temp\CPCM\cpcm.py`
- `D:\AI_Temp\CPCM\cpcm\`
- `D:\AI_Temp\CPCM\web\`
- `D:\AI_Temp\CPCM\icon.png`
- `D:\AI_Temp\CPCM\install-cpcm.sh`
- `D:\AI_Temp\CPCM\AUTOR.txt` mit der Zeile `Rolle: Windows-Referenz`

Python auf Linux:

```bash
python3 --version
```

Erforderlich ist 3.11 oder neuer. Unter Debian oder Ubuntu, falls der Befehl fehlt:

```bash
sudo apt-get update
sudo apt-get install -y python3
```

Weitere Pakete braucht CPCM nicht.

## 2. Weg A – dieselbe Partition

Wenn Linux die Windows-Partition lesen kann und `D:\AI_Temp\CPCM` dort sichtbar ist, zum Beispiel als `/mnt/windows/AI_Temp/CPCM`:

```bash
cd /mnt/windows/AI_Temp/CPCM
chmod 755 cpcm.py cpcm.sh install-cpcm.sh
./install-cpcm.sh "$HOME/AI_Temp/CPCM"
```

`install-cpcm.sh` kopiert das Programm nach `~/AI_Temp/CPCM`, lässt einen schon vorhandenen Vault in Ruhe und schreibt einen Menüeintrag `~/.local/share/applications/cpcm.desktop` mit absolutem Icon-Pfad. Quelle und Ziel dürfen nicht derselbe Ordner sein.

Den Vault der Windows-Fassung nicht in die Kopie ziehen, wenn beide Systeme dieselben Sicherungen sehen sollen. In der Oberfläche unter **Welten** den Vault auf den gemounteten Ordner setzen, zum Beispiel:

```text
/mnt/windows/AI_Temp/CPCM/vault
```

## 3. Weg B – Kopie ohne gemountete Partition

Den Ordner `D:\AI_Temp\CPCM` als Zip oder Stick auf den Linux-Rechner bringen. Den Vault nur mitkopieren, wenn die Sicherungen mitwandern sollen.

```bash
mkdir -p "$HOME/src"
unzip CPCM-windows.zip -d "$HOME/src/CPCM"
cd "$HOME/src/CPCM"
chmod 755 cpcm.py cpcm.sh install-cpcm.sh
./install-cpcm.sh
```

Ohne Argument ist das Ziel `$HOME/AI_Temp/CPCM`.

## 4. Start

```bash
"$HOME/AI_Temp/CPCM/cpcm.sh"
```

Oder über das Anwendungsmenü „CPCM“. Die Seite ist `http://127.0.0.1:8765/`. Kopfzeile: Vault-Pfad und „Andreas Meyer · ame@sellerbach.de“.

Prüfung ohne Browser:

```bash
cd "$HOME/AI_Temp/CPCM"
python3 -m unittest discover -s tests -p 'test_cpcm_*.py'
python3 cpcm.py serve --no-browser
```

In einer zweiten Shell:

```bash
curl -sS http://127.0.0.1:8765/api/status
```

Die Antwort enthält `"author": "Andreas Meyer"` und `"author_email": "ame@sellerbach.de"`.

## 4a. Kompilierte Fassung

Binary: `dist/CPCM` (eine Datei, gebaut mit PyInstaller aus `CPCM.spec`). Installer: `install-cpcm-bin.sh`. Eine Windows-EXE liegt daneben nicht.

```bash
chmod 755 install-cpcm-bin.sh
./install-cpcm-bin.sh
```

Ohne Argument ist das Ziel `$HOME/AI_Temp/CPCM`. Das Skript kopiert `dist/CPCM` dorthin, macht `CPCM` und `cpcm.sh` ausführbar, schreibt `AUTOR.txt` mit der Rolle `Linux-Nachbau der Windows-Referenz` und setzt `~/.local/share/applications/cpcm.desktop`. Ein vorhandener `vault/` bleibt. Quelle und Ziel dürfen nicht derselbe Ordner sein.

Start über das Menü „CPCM“, oder:

```bash
"$HOME/AI_Temp/CPCM/cpcm.sh"
"$HOME/AI_Temp/CPCM/CPCM" serve
```

Die Seite ist `http://127.0.0.1:8765/`. Neu bauen im Quellordner: `python3 -m PyInstaller --noconfirm --clean CPCM.spec`.

## 5. Beide Welten verbinden

Unter **Welten**:

- Linux-Home: der echte Pfad, zum Beispiel `/home/andreas`
- Windows-Home: derselbe Pfad wie in der Windows-Fassung, zum Beispiel `C:\Users\Andreas`

Eine Datei aus dem Home sichern. In der Auswahl muss die Windows-Spalte unter `C:\Users\...` stehen und die Linux-Spalte unter `/home/...`. Wiederherstellen auf Linux schreibt nach `~/Documents`, `~/.config` oder `~/.local/share`, je nach Vault-Präfix `documents/`, `config/` oder `local/`.

`AUTOR.txt` im Linux-Ordner muss `Rolle: Linux-Nachbau der Windows-Referenz` enthalten.

## 6. Grenzen

- Die Oberfläche bindet nur an `127.0.0.1`.
- Paketbefehle werden angezeigt und nicht von selbst ausgeführt.
- NTFS, ext4 und Btrfs werden nur zur Prüfung beschrieben. `chkdsk` bleibt Windows, `fsck` bleibt Linux.
- Spannungs-Offsets werden gespeichert und nicht an die Hardware geschrieben.
- Eine Ladeschwelle wird nur geschrieben, wenn die sysfs-Datei existiert und für den Benutzer beschreibbar ist.
