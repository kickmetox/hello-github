"""Klartext für Windows-Codes, NTSTATUS und Linux-Signaturen.

HRESULT mit Facility Win32: 0x80070000 | Win32-Code.
"""

from __future__ import annotations

CODES: dict[str, dict] = {
    "0x80070002": {
        "title": "Datei nicht gefunden",
        "plain_de": "Win32-Fehler 2 (ERROR_FILE_NOT_FOUND), verpackt als HRESULT 0x80070002. Eine Datei, ein Paket oder ein Update-Ziel, das der Aufrufer erwartet, ist am genannten Pfad nicht da.",
        "likely": ["Pfad oder Paketname stimmt nicht", "Datei wurde verschoben", "Windows-Update findet die Payload nicht"],
    },
    "0x80070003": {
        "title": "Pfad nicht gefunden",
        "plain_de": "Win32-Fehler 3 (ERROR_PATH_NOT_FOUND). Ein Verzeichnis auf dem Weg zur Datei existiert nicht. Das ist ein anderer Befund als eine fehlende Datei im vorhandenen Ordner.",
        "likely": ["Elternverzeichnis fehlt", "Laufwerk nicht verbunden", "Tippfehler im Pfad"],
    },
    "0x80070005": {
        "title": "Zugriff verweigert",
        "plain_de": "Win32-Fehler 5 (ERROR_ACCESS_DENIED), HRESULT 0x80070005. Das Konto, das Token oder die ACL lässt den Zugriff nicht zu. Das ist keine defekte Datei.",
        "likely": ["Fehlende Administratorrechte", "Schreibschutz", "Dienstkonto ohne Recht auf den Ordner"],
    },
    "0x80004005": {
        "title": "Nicht spezifizierter Fehler",
        "plain_de": "E_FAIL (0x80004005) sagt nur, dass die Operation gescheitert ist. Die Ursache steht in der Meldung darüber oder im inneren HRESULT, nicht im Code selbst.",
        "likely": ["Abgebrochene COM-Operation", "Update ohne genauere innere Meldung", "Treiber oder Dienst hat allgemein abgelehnt"],
    },
    "0x80070057": {
        "title": "Ungültiger Parameter",
        "plain_de": "Win32-Fehler 87 (ERROR_INVALID_PARAMETER), HRESULT 0x80070057. Ein Argument, ein Registry-Wert oder eine Struktur hat ein Format, das die API nicht annimmt.",
        "likely": ["Falscher Datentyp in der Registry", "Leerer Pflichtparameter", "API mit unpassender Strukturgröße aufgerufen"],
    },
    "0xc0000005": {
        "title": "Zugriffsverletzung",
        "plain_de": "NTSTATUS 0xC0000005 (STATUS_ACCESS_VIOLATION). Der Prozess hat Speicher gelesen oder geschrieben, der ihm nicht gehört. Das ist ein Programmfehler oder ein defektes Modul, kein fehlendes Recht im ACL-Sinn.",
        "likely": ["Fehlerhafte DLL oder .so im Prozess", "Treiber im Kernelmodus", "Beschädigte Installation des Programms"],
    },
    "0xc0000135": {
        "title": "DLL nicht gefunden",
        "plain_de": "NTSTATUS 0xC0000135 (STATUS_DLL_NOT_FOUND). Der Lader findet eine benötigte DLL nicht im Suchpfad.",
        "likely": ["Visual-C++-Runtime fehlt", "Programmverzeichnis unvollständig", "PATH zeigt nicht auf die DLL"],
    },
    "0xc0000142": {
        "title": "DLL-Initialisierung gescheitert",
        "plain_de": "NTSTATUS 0xC0000142 (STATUS_DLL_INIT_FAILED). Die DLL wurde gefunden, ihr Startcode (DllMain) ist aber fehlgeschlagen.",
        "likely": ["Abhängige DLL fehlt trotzdem", "Architektur 32/64 passt nicht", "Defekte Laufzeitbibliothek"],
    },
    "0x8007007e": {
        "title": "Modul nicht gefunden",
        "plain_de": "Win32-Fehler 126 (ERROR_MOD_NOT_FOUND), HRESULT 0x8007007E. LoadLibrary findet das Modul oder eine seiner Abhängigkeiten nicht.",
        "likely": ["DLL fehlt", "Abhängigkeit der DLL fehlt", "Falsche Architektur"],
    },
    "0x80070020": {
        "title": "Datei wird verwendet",
        "plain_de": "Win32-Fehler 32 (ERROR_SHARING_VIOLATION). Eine andere Handle hält die Datei so offen, dass dieser Zugriff nicht erlaubt ist.",
        "likely": ["Installer läuft bereits", "Antivirenscanner", "Datei in einem Editor offen"],
    },
    "0x80070422": {
        "title": "Dienst ist deaktiviert",
        "plain_de": "Win32-Fehler 1058 (ERROR_SERVICE_DISABLED). Der Dienst, den die Aktion brauchte, steht auf Deaktiviert und kann nicht gestartet werden.",
        "likely": ["Windows Update Dienst", "BITS", "Gruppenrichtlinie hat den Dienst abgeschaltet"],
    },
    "0x80070643": {
        "title": "Installation fehlgeschlagen",
        "plain_de": "Win32-Fehler 1603 (ERROR_INSTALL_FAILURE). Das MSI oder das Update hat die Installation abgebrochen. Der Code allein nennt nicht die innere Ursache.",
        "likely": ["Vorgängerversion blockiert", "Fehlende Laufzeit", "Abbruch in einer Custom Action"],
    },
    "0x80070070": {
        "title": "Datenträger voll",
        "plain_de": "Win32-Fehler 112 (ERROR_DISK_FULL). Auf dem Zielvolume ist kein Platz mehr für die Schreiboperation.",
        "likely": ["Systemlaufwerk voll", "WinSxS oder Temp groß", "Profilquota"],
    },
    "0x8007000e": {
        "title": "Nicht genug Speicher",
        "plain_de": "Win32-Fehler 14 (ERROR_OUTOFMEMORY) bzw. die gleiche Bitmaske wie E_OUTOFMEMORY. Der Prozess konnte den angeforderten Speicher nicht bekommen.",
        "likely": ["RAM erschöpft", "Adressraum 32-Bit am Limit", "Commit-Limit erreicht"],
    },
    "0x80072ee7": {
        "title": "Servername nicht aufgelöst",
        "plain_de": "WinINet-Fehler 12007 (ERROR_INTERNET_NAME_NOT_RESOLVED), HRESULT 0x80072EE7. Der DNS-Name des Ziels wurde nicht aufgelöst.",
        "likely": ["DNS", "Kein Netz", "Proxy oder Hosts-Datei"],
    },
    "0x80072efd": {
        "title": "Verbindung fehlgeschlagen",
        "plain_de": "WinINet-Fehler 12029 (ERROR_INTERNET_CANNOT_CONNECT), HRESULT 0x80072EFD. Der Name ist bekannt, die TCP-Verbindung kommt aber nicht zustande.",
        "likely": ["Firewall", "Proxy", "Zielport geschlossen"],
    },
    "0x80072f8f": {
        "title": "Zertifikat zeitlich ungültig",
        "plain_de": "WinINet-Fehler 12037 (CERT_E_EXPIRED / DATE_INVALID als WinINet-Code), HRESULT 0x80072F8F. Das TLS-Zertifikat liegt außerhalb seiner Gültigkeit, oft weil die Uhr falsch geht.",
        "likely": ["Systemuhr", "Abgelaufenes Zertifikat", "Falsche Root-Zertifikate"],
    },
    "0x8024402c": {
        "title": "Windows Update erreicht den Namen nicht",
        "plain_de": "WU_E_PT_WINHTTP_NAME_NOT_RESOLVED (0x8024402C). Der Update-Client konnte den Namen des Update-Endpunkts nicht auflösen.",
        "likely": ["DNS", "WSUS-URL falsch", "Kein Netz"],
    },
    "0x0000007b": {
        "title": "Startgerät nicht erreichbar",
        "plain_de": "Bugcheck 0x0000007B (INACCESSIBLE_BOOT_DEVICE). Windows findet beim Start den Datenträger mit der Systempartition nicht. Das ist ein Firmware-/Treiber-/AHCI-Thema, kein CrossOS-Ein-Klick.",
        "likely": ["Storage-Treiber fehlt nach Hardwarewechsel", "BIOS-Modus AHCI/RAID geändert", "Defektes Startvolume"],
    },
    "0x000000ef": {
        "title": "Kritischer Prozess beendet",
        "plain_de": "Bugcheck 0x000000EF (CRITICAL_PROCESS_DIED). Windows hat einen Prozess beendet, ohne den es nicht weiterläuft. Die Ursache steht im Dump, nicht im Code allein.",
        "likely": ["Speicherfehler", "Treiber", "Beschädigte Systemdatei"],
    },
    "event-41": {
        "title": "Kernel-Power 41",
        "plain_de": "Ereignis 41 von Kernel-Power bedeutet, dass das System neu startete, ohne sauber herunterzufahren. Es nennt nicht die Ursache. Die steht im Bugcheck davor oder in der Hardware.",
        "likely": ["Stromverlust", "Überhitzung", "Hänger im Treiber"],
    },
    "event-1000": {
        "title": "Anwendungsfehler 1000",
        "plain_de": "Ereignis 1000 ist ein abgestürztes Programm im Benutzermodus. Modulname und Exception-Code in derselben Meldung sind die eigentliche Spur.",
        "likely": ["Fehlerhafte DLL", "Zugriffsverletzung", "Fehlende Laufzeit"],
    },
    "event-1001": {
        "title": "Windows Error Reporting 1001",
        "plain_de": "Ereignis 1001 fasst einen Absturz oder Bugcheck für die Fehlerberichterstattung zusammen. Der Bugcheck-Code in der Meldung ist aussagekräftiger als die 1001 selbst.",
        "likely": ["Folgeereignis eines Absturzes"],
    },
    "event-7031": {
        "title": "Dienst unerwartet beendet",
        "plain_de": "Ereignis 7031 des Service Control Manager: Ein Dienst ist unerwartet beendet worden. Die Dienstmeldung und das zugehörige Anwendungsereignis erklären den Abbruch.",
        "likely": ["Dienstcrash", "Abhängigkeit fehlt", "Konfiguration ungültig"],
    },
    "event-10016": {
        "title": "DCOM-Berechtigung 10016",
        "plain_de": "Ereignis 10016 ist eine abgelehnte lokale COM-Aktivierung. Auf einem Einzelplatzrechner ist das häufig Rauschen der Standard-App-IDs und kein Defekt, der ein Recht auf CLSID verlangt.",
        "likely": ["Normales DCOM-Rauschen", "Nur relevant, wenn eine konkrete App deshalb ausfällt"],
    },
    "segfault": {
        "title": "Speicherzugriffsfehler",
        "plain_de": "Segmentation fault heißt: der Prozess hat eine Adresse benutzt, die ihm der Kernel nicht erlaubt. „core dumped“ bedeutet, dass ein Speicherabbild geschrieben wurde, wenn das Limit das zulässt. Das ist ein Fehler im Programm oder in einer Bibliothek, kein fehlendes sudo.",
        "likely": ["Fehler im Programm", "Kaputte native Erweiterung", "Bibliothek passt nicht zur Erwartung des Programms"],
    },
    "missing-so": {
        "title": "Gemeinsame Bibliothek fehlt",
        "plain_de": "Der dynamische Lader findet eine .so nicht. Der Dateiname in der Meldung ist die fehlende Bibliothek. Das Paket, das sie liefert, hängt von der Distribution ab und wird nur vorgeschlagen, nicht installiert.",
        "likely": ["Paket nicht installiert", "ldconfig-Cache veraltet", "Falsche Multiarch-Architektur"],
    },
    "missing-dll": {
        "title": "DLL fehlt",
        "plain_de": "Windows findet eine DLL nicht, die das Programm beim Start laden will. Häufig ist es die Visual-C++-Laufzeit, nicht eine beliebige Datei, die man aus dem Internet nachlegt.",
        "likely": ["VC++ Redistributable fehlt", "Unvollständige Programminstallation"],
    },
    "apt-broken": {
        "title": "Paketabhängigkeiten gebrochen",
        "plain_de": "dpkg oder apt meldet unerfüllte Abhängigkeiten oder ein halb konfiguriertes Paket. Der sichere erste Schritt ist eine Prüfung ohne Änderung. Eine Reparaturinstallation bleibt ein Plan.",
        "likely": ["Unterbrochene Installation", "Konflikt zweier Paketversionen", "PPA-Paket ohne passende Abhängigkeit"],
    },
    "systemd-failed": {
        "title": "systemd-Unit fehlgeschlagen",
        "plain_de": "Eine Unit ist in den Zustand failed gegangen. Der Unit-Name und die Zeilen aus journalctl -u erklären den Abbruch. Ein Neustart der Unit ist nicht freigegeben.",
        "likely": ["ExecStart endet mit Fehler", "Abhängige Unit fehlt", "Konfiguration ungültig"],
    },
    "oom": {
        "title": "Speicher aufgebraucht",
        "plain_de": "Der Kernel hat einen Prozess beendet, weil der Speicher nicht mehr reichte (OOM-Killer). Das ist eine Folge von RAM- oder Swap-Mangel, kein Paketfehler.",
        "likely": ["Zu wenig RAM", "Speicherleck", "Swap fehlt"],
    },
    "io-error": {
        "title": "E/A-Fehler des Datenträgers",
        "plain_de": "Der Kernel konnte einen Block nicht lesen oder schreiben. Das deutet auf Datenträger, Kabel, Controller oder ein sterbendes Medium. CrossOS repariert das nicht.",
        "likely": ["Defekter Datenträger", "Lockeres Kabel", "Controller-Fehler"],
    },
    "ext4-error": {
        "title": "ext4 meldet einen Fehler",
        "plain_de": "Das ext4-Dateisystem hat eine Inkonsistenz oder einen E/A-Fehler gemeldet. Eine Prüfung gehört mit fsck im nicht gemounteten Zustand auf das Linux, dem das Dateisystem gehört. CrossOS startet kein fsck.",
        "likely": ["Unsauberes Aushängen", "Datenträgerfehler", "Journal nicht wiederholbar"],
    },
    "readonly-fs": {
        "title": "Dateisystem nur lesbar",
        "plain_de": "Das Dateisystem wurde auf nur-lesen umgestellt oder war nie schreibbar. Häufige Ursache ist ein vorheriger E/A-Fehler, nach dem der Kernel das Volume schützt.",
        "likely": ["Vorheriger I/O-Fehler", "Mount-Option ro", "Volles oder defektes Medium"],
    },
    "kernel-panic": {
        "title": "Kernel-Panic",
        "plain_de": "Der Kernel hat angehalten. Das ist kein Benutzerprogramm mehr. Ursache sind meist Treiber, RAM oder ein beschädigtes Root-Dateisystem. Es gibt keinen Ein-Klick-Repair.",
        "likely": ["Treiber", "RAM", "Root-Dateisystem"],
    },
}


def lookup(code: str) -> dict | None:
    return CODES.get(code.lower())
