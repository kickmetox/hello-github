# Flare

Spotlight-ähnlicher Starter für Windows 11. Er sucht Programme, Ordner und
Dateien, läuft im Hintergrund und lässt sich aus anderen Programmen abfragen.

Kompletter Arbeitsbaum als Zip (Quellcode, Tests, Build und Installer):
[flare-workspace-complete.zip](https://github.com/kickmetox/hello-github/raw/cursor/flare-spotlight-a293/flare-workspace-complete.zip)

Standardkürzel: **Strg+Alt+Leertaste**. Es greift, während ein anderes Fenster
den Fokus hat. In `config.json` steht das Kürzel als `ctrl+alt+space`.

## Einrichtung

Installer für 64-Bit-Windows 11: `dist/windows/Flare-Setup-1.0.0.exe`.

Er richtet Flare ohne Administrator unter `%LOCALAPPDATA%\Programs\Flare` ein,
legt einen Startmenü-Eintrag an und kann „Mit Windows starten“ setzen. Der
Katalog bleibt getrennt unter `%LOCALAPPDATA%\Flare` und wird beim Entfernen
nicht gelöscht. Die Einrichtung ist nicht signiert, Windows SmartScreen kann
deshalb nachfragen.

Danach liegt Flare im Startmenü. Strg+Alt+Leertaste öffnet die Suche aus
anderen Programmen.

## Starten

Im Startmenü oder über die Verknüpfung. Aus einem Quellbaum auf Windows 11:

```bat
py -3 flare.py
```

Damit läuft der Dienst und das Suchfenster geht auf. Ein zweiter Start holt
das laufende Fenster nach vorn.

Nur im Hintergrund, bis das Kürzel kommt (so startet auch der Autostart):

```bat
py -3 flare.py --background
```

Nur bestimmte Ordner:

```bat
py -3 flare.py --roots %USERPROFILE%\Documents %USERPROFILE%\Downloads
```

## Mit der Anmeldung

Der Installer setzt das auf Wunsch selbst. Aus dem Quellbaum:

```bat
py -3 flare.py install-autostart
py -3 flare.py remove-autostart
```

Der Eintrag liegt in
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Flare`. Für eine
Python-Installation wird `pythonw.exe` genutzt, falls vorhanden, damit keine
Konsole erscheint. Das eingefrorene Programm trägt `Flare.exe --background`
ein. Das Fenster öffnet erst das Kürzel.

## Andere Programme

Der Dienst hört nur auf `127.0.0.1`, Port `47731` (oder dem nächsten freien).

```bat
py -3 flare.py query --json "rechnung"
py -3 flare.py query "rechnung" --open
curl -s "http://127.0.0.1:47731/api/search?q=rechnung"
curl -s -X POST "http://127.0.0.1:47731/api/activate"
```

```python
from flare.client import Client

client = Client()
print(client.search("rechnung"))
client.open_id(client.search("rechnung")["results"][0]["id"])
```

Läuft kein Dienst, liest `Client.search` die Datenbank nur lesend.

| Methode | Pfad | Bedeutung |
| --- | --- | --- |
| GET | `/api/search?q=&limit=` | Trefferliste |
| GET | `/api/status` | Einträge, CPU/CUDA, Indexphase |
| POST | `/api/open` | `{"id": 12}` öffnet einen Katalogtreffer |
| POST | `/api/activate` | Fenster holen |
| POST | `/api/reindex` | Ordnerstände verwerfen und neu lesen |
| GET | `/api/events?since=` | langes Warten auf `focus` |

Treffer haben `id`, `kind` (`app`, `file`, `dir`, `calc`), `name`, `path`,
`detail`, `via`, `score`. Eine reine Rechnung wie `2+2*3` steht oben; Enter
kopiert das Ergebnis.

## Was indiziert wird

Zuerst Programme aus dem Startmenü (`.lnk`) und aus `PATH` (`.exe`, `.bat`,
`.cmd`, `.com`). Danach die bekannten Ordner Desktop, Dokumente, Downloads,
Bilder, Musik und Videos, auch wenn Windows sie nach OneDrive verschoben hat.
Anschließend das Benutzerprofil. Ausgelassen werden unter anderem
`node_modules`, `.git`, versteckte Ordner, Caches und Schlüsseldateien
(`id_rsa`, `.env`, `*.pem`).

Dateinamen immer. Textinhalt nur in den heißen Ordnern, nur bis 64 KiB, nur
die ersten 4 KiB, nur bekannte Textendungen.

## Last

Der Index-Thread hält ein Tastverhältnis von etwa 8 %. Die ersten Sekunden
liegen bei 40 %, damit Programme und Dokumente schnell da sind. Ist die CPU
bereits belegt (Idle unter 20 %), wird zusätzlich gewartet. Der Index-Thread
läuft im Windows-Hintergrundmodus. Volle Läufe wiederholen sich alle
90 Sekunden (Programme), 5 Minuten (heiße Ordner) und 20 Minuten (Rest).

Unveränderte Ordner kosten beim nächsten Lauf nur `stat` plus die gespeicherte
Kindliste, kein `readdir`. Heiße Wurzeln bekommen eine Änderungsanzeige;
gelesen wird danach nur, wo sich die Ordner-mtime geändert hat. Liegen Anlegen
und Löschen im selben Zeitstempel, zieht das Watcher-Flag den Ordner sofort
neu. Ohne Meldung passiert das spätestens nach 15 Minuten.

Die Suche nutzt den B-Tree für Präfixe (auch ein oder zwei Zeichen) und
FTS5-Trigramme für Teilstrings. Tippfehler werden nur nachgezogen, wenn die
genauen Treffer nicht reichen, und nur über den Anteil gemeinsamer Trigramme.

CUDA wird benutzt, wenn `nvcuda.dll` einen Rechner meldet. Dann bewertet ein
kleiner PTX-Kern größere Tippfehler-Mengen auf der GPU. Ohne Treiber bleibt es
bei derselben Rechnung auf der CPU. `FLARE_FORCE_CPU=1` schaltet die GPU aus.

## Konfiguration

`%APPDATA%\Flare\config.json`:

```json
{
  "hotkey": "ctrl+alt+space",
  "duty": 0.08,
  "content": true,
  "port": 47731,
  "extra_roots": []
}
```

Der Katalog liegt unter `%LOCALAPPDATA%\Flare\`.

## Installer neu bauen

Auf einem Linux-Rechner mit Wine und NSIS:

```bash
bash packaging/windows/build.sh
```

Das Ergebnis ist `dist/windows/Flare-Setup-1.0.0.exe`.

## Tests

```bash
python3 -m unittest discover -s tests
```
