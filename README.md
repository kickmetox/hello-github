# Flare

Spotlight-ähnlicher Starter für Windows 11. Er sucht Programme, Ordner und
Dateien in einem eigenen Fenster, läuft im Hintergrund und lässt sich aus
anderen Programmen abfragen.

Kompletter Arbeitsbaum als Zip (Quellcode, Tests, Build und Installer):
[flare-workspace-voll.zip](https://github.com/kickmetox/hello-github/raw/cursor/flare-spotlight-a293/flare-workspace-voll.zip)

Das Fenster ist ein normales Win32-Fenster. Es startet keinen Browser.
Schließen blendet es nur aus; der Index läuft weiter, Strg+Alt+Leertaste holt es zurück.
Standardkürzel: **Strg+Alt+Leertaste**. Es greift, während ein anderes Fenster
den Fokus hat. In `config.json` steht das Kürzel als `ctrl+alt+space`.
**Hilfe** im Fenster oder die Taste F1 öffnet im selben Programm eine
Kurzbeschreibung, einen Beschreibungstext und die Feature-Liste. Escape
schließt die Hilfe und kehrt zur Suche zurück. Es öffnet sich kein Browser.
**Ähnlich** schaltet die Ähnlichkeitssuche ein, im Fenster als „Ähnliche Namen“
und in der Web-Oberfläche als Knopf. Nahe Dateinamen bleiben sichtbar, auch
wenn schon genaue Treffer da sind. Der Web-Knopf merkt sich die Wahl
(`localStorage`, Schlüssel `flare-similar`) und zeigt unter solchen Treffern
„ähnlich NN %“. Ab 32 Kandidaten rechnet die Grafikkarte den Recall, wenn
`nvcuda.dll` einen Rechner meldet.

## Einrichtung

Installer für 64-Bit-Windows 11: `dist/windows/Flare-Setup-1.0.0.exe`.

Er richtet Flare ohne Administrator unter `%LOCALAPPDATA%\Programs\Flare` ein,
legt einen Startmenü-Eintrag an und kann „Mit Windows starten“ setzen. Läuft
Flare schon, beendet das Setup `Flare.exe`, wartet kurz und ersetzt danach
`_internal`, damit gesperrte DLLs die Einrichtung nicht anhalten. Der Katalog
bleibt getrennt unter `%LOCALAPPDATA%\Flare` und wird beim Entfernen nicht
gelöscht. Die Einrichtung ist nicht signiert, Windows SmartScreen kann
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
py -3 flare.py query --similar --json "bericht"
py -3 flare.py query "rechnung" --open
curl -s "http://127.0.0.1:47731/api/search?q=bericht&similar=1"
curl -s "http://127.0.0.1:47731/api/search?q=rechnung"
curl -s -X POST "http://127.0.0.1:47731/api/activate"
```

```python
from flare.client import Client

client = Client()
print(client.search("bericht", similar=True))
client.open_id(client.search("rechnung")["results"][0]["id"])
```

Läuft kein Dienst, liest `Client.search` die Datenbank nur lesend.

| Methode | Pfad | Bedeutung |
| --- | --- | --- |
| GET | `/api/search?q=&limit=&similar=1` | Trefferliste, mit `similar=1` auch nahe Namen |
| GET | `/api/status` | Einträge, CPU/CUDA, Indexphase |
| POST | `/api/open` | `{"id": 12}` öffnet einen Katalogtreffer |
| POST | `/api/activate` | Fenster holen |
| POST | `/api/reindex` | Ordnerstände verwerfen und neu lesen |
| GET | `/api/events?since=` | langes Warten auf `focus` |

Treffer haben `id`, `kind` (`app`, `file`, `dir`, `calc`), `name`, `path`,
`detail`, `via`, `score`. Mit `similar=1` oder `--similar` kommt bei nahen
Namen zusätzlich `via` = `similar` und `similarity` zwischen 0 und 1.
Eine reine Rechnung wie `2+2*3` steht oben; Enter kopiert das Ergebnis.

## Was indiziert wird

Zuerst Programme aus dem Startmenü (`.lnk`) und aus `PATH` (`.exe`, `.bat`,
`.cmd`, `.com`). Danach die bekannten Ordner Desktop, Dokumente, Downloads,
Bilder, Musik und Videos, auch wenn Windows sie nach OneDrive verschoben hat.
Anschließend das Benutzerprofil. Externe Festplatten und USB-Sticks werden
eigene Wurzeln, auch wenn eine externe Platte als festes Laufwerk erscheint.
Lokale Ordner von OneDrive, Dropbox und Google Drive kommen dazu, soweit sie
auf der Platte liegen. Nur-online-Platzhalter zählen mit Namen, ihr Inhalt
wird nicht geladen.

Das Systemlaufwerk wird nicht vollständig gelesen. CD-Laufwerke entfallen.
Gemappte Netzlaufwerke bleiben aus, solange `index_network` nicht `true` ist;
dann nur Dateinamen, mit derselben Last wie das Benutzerprofil. Freigaben
ohne Laufwerksbuchstaben sucht Flare nicht. Keine Websuche, keine E-Mail,
keine Kontakte und keine Chats.

Ausgelassen werden unter anderem `node_modules`, `.git`, versteckte Ordner,
Caches und Schlüsseldateien (`id_rsa`, `.env`, `*.pem`).

Dateinamen immer. Textinhalt nur in den heißen Ordnern, nur bis 64 KiB, nur
die ersten 4 KiB, nur bekannte Textendungen.

## Last

Der Index-Thread hält ein Tastverhältnis von etwa 35 %. Die ersten 20 Sekunden
liegen bei 85 %, damit Programme und Dokumente schnell da sind. Ist die CPU
bereits belegt (Idle unter 20 %), wird zusätzlich gewartet. Schreiben in den
Katalog läuft gesammelt, der Seitencache ist groß. Volle Läufe wiederholen sich alle
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
kleiner PTX-Kern ab 32 Kandidaten den Trigramm-Recall auf der GPU. Dieselbe
Rechnung läuft sonst auf der CPU. `FLARE_FORCE_CPU=1` schaltet die GPU aus.

Die Ähnlichkeitssuche ist ein eigener Modus (`--similar`, `similar=1`, Knopf
**Ähnlich**). Sie bewertet nahe Namen auch dann, wenn genaue Treffer die Liste
schon füllen. Bis 3000 Einträge wird der ganze Katalog bewertet, darüber die
FTS-Trigramm-Kandidaten. Ein Name zählt ab 0,5, als Maximum aus Dice und
Recall, damit Tippfehler und fast gleiche Namen beide treffen. Etwa die Hälfte
der Plätze bleibt bei den lexikalischen Treffern, der Rest zeigt nahe Namen.
Ohne den Schalter bleibt der bisherige Nachzug: Tippfehler nur, wenn die
starken Treffer nicht reichen.

## Konfiguration

`%APPDATA%\Flare\config.json`:

```json
{
  "hotkey": "ctrl+alt+space",
  "duty": 0.35,
  "content": true,
  "port": 47731,
  "extra_roots": [],
  "exclude_drives": [],
  "index_network": false
}
```

`exclude_drives` ist die Ausschlussliste: Laufwerke wie `"E:\\"` oder eine
Datenträgerbezeichnung. Sie werden nicht indiziert. `index_network` steht
standardmäßig auf `false`; `true` liest gemappte Netzlaufwerke nur nach Namen.

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
