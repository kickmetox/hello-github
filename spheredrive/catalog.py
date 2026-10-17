"""Statische Fachtexte: Vergleich, Link-Arten und Anbieter."""

from __future__ import annotations

LINK_KINDS: list[tuple[str, str]] = [
    ("junction", "Verzeichnis-Junction (mklink /J)"),
    ("symlink_dir", "Symbolischer Ordnerlink (mklink /D)"),
    ("symlink_file", "Symbolischer Dateilink (mklink)"),
    ("hardlink", "Harte Dateiverknüpfung (mklink /H)"),
]

LINK_KIND_LABEL = {key: label for key, label in LINK_KINDS}

PS_PROVIDERS: list[tuple[str, str, str]] = [
    ("FileSystem", "FileSystem", "Ordnerpfad oder UNC, z. B. C:\\Projekte oder \\\\server\\freigabe"),
    ("Registry", "Registry", "Registrierungspfad, z. B. HKLM:\\SOFTWARE oder HKCU:\\Software"),
    ("Certificate", "Certificate", "Zertifikatspeicher, z. B. Cert:\\CurrentUser\\My"),
    ("Variable", "Variable", "Optional ein Gültigkeitsbereich, sonst leer lassen"),
    ("Environment", "Environment", "Optional ein Präfix, sonst leer lassen"),
    ("Function", "Function", "Funktionslaufwerk, Stamm meist leer"),
    ("Alias", "Alias", "Aliaslaufwerk, Stamm meist leer"),
    ("WSMan", "WSMan", "WinRM-Ziel, z. B. ein Remote-Computer"),
]

PERMISSIONS: list[tuple[str, str]] = [
    ("READ", "Lesen"),
    ("CHANGE", "Ändern"),
    ("FULL", "Vollzugriff"),
]

COMPARISON: list[dict[str, str]] = [
    {
        "befehl": "subst",
        "ziel": "Lokaler Ordner",
        "erstellt": "Virtuelles Laufwerk (z. B. X:)",
        "neustart": "Nein",
        "spheredrive": "Autostart, mit Adminrechten zusätzlich DOS Devices",
    },
    {
        "befehl": "net use",
        "ziel": "Netzwerkfreigabe",
        "erstellt": "Virtuelles Laufwerk (z. B. X:)",
        "neustart": "Ja, mit /persistent:yes",
        "spheredrive": "Dauerhaft schaltbar, Bezeichnung und Symbol",
    },
    {
        "befehl": "mklink /D",
        "ziel": "Lokaler Ordner",
        "erstellt": "Symbolischen Ordnerlink",
        "neustart": "Ja, im Dateisystem",
        "spheredrive": "Anlegen und Entfernen nur der Verknüpfung",
    },
    {
        "befehl": "mklink /J",
        "ziel": "Lokaler Ordner",
        "erstellt": "Junction, wirkt wie ein echter Ordner",
        "neustart": "Ja, im Dateisystem",
        "spheredrive": "Ohne Administratorrechte, mit Zielprüfung",
    },
    {
        "befehl": "New-PSDrive",
        "ziel": "Ordner, Registry, Zertifikate",
        "erstellt": "PowerShell-Laufwerk",
        "neustart": "Nein, nur in der Sitzung",
        "spheredrive": "Eintrag im PowerShell-Profil; -Persist nur bei UNC",
    },
    {
        "befehl": "mountvol / diskmgmt",
        "ziel": "Partition oder VHD/VHDX",
        "erstellt": "Buchstaben oder Ordner-Bereitstellung",
        "neustart": "Ja, über den Volume-Manager",
        "spheredrive": "Leeren NTFS-Ordner oder Buchstaben, plus diskmgmt.msc",
    },
]

GUIDE: list[tuple[str, str]] = [
    (
        "Tiefer Projektordner als Laufwerk",
        "Subst. SphereDrive setzt Bezeichnung, Symbol, Papierkorb und die Wiederherstellung nach dem Neustart.",
    ),
    (
        "NAS, Server oder bereits freigegebener Ordner",
        "net use. Mit „Dauerhaft“ bleibt die Verbindung über /persistent:yes erhalten.",
    ),
    (
        "Ordner an anderer Stelle, ohne neuen Buchstaben",
        "Junction (mklink /J). Für ältere Programme verhält sie sich wie ein physischer Ordner.",
    ),
    (
        "Nur in PowerShell, Registry oder Zertifikate",
        "New-PSDrive. Ohne Profil gilt das Laufwerk nur in der geöffneten Sitzung.",
    ),
    (
        "Echte Partition oder VHD in einen leeren Ordner",
        "Bereitstellungspunkt. Alternativ denselben Schritt in der Datenträgerverwaltung ausführen.",
    ),
]

NAV_ITEMS: list[tuple[str, str]] = [
    ("overview", "Übersicht"),
    ("subst", "Subst"),
    ("net", "Netzlaufwerke"),
    ("links", "Verknüpfungen"),
    ("ps", "PowerShell"),
    ("mounts", "Bereitstellung"),
    ("compare", "Vergleich"),
    ("settings", "Einstellungen"),
]
