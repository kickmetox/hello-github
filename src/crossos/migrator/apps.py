"""Anwendungskatalog und Gleichwertigkeitsplan.

„Gleich“ bedeutet dasselbe Programm. „Port“ ist ein naher Nachbau.
„Workflow“ ist eine Arbeitsalternative und ausdrücklich kein 1:1-Ersatz.
"""

from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache

from crossos.migrator.packages import PackageBridge
from crossos.safety import SafetyError

# equivalence: same | port | workflow
CATALOG: list[dict] = [
    {
        "id": "notepadpp",
        "names": ["notepad++", "notepadpp", "notepadplusplus"],
        "summary_de": "Notepad++ hat keinen offiziellen Linux-Port. Notepad-Next ist der Scintilla-Nachbau, kein Byte-für-Byte-Ersatz.",
        "equivalence": "port",
        "windows": {"winget": "Notepad++.Notepad++", "scoop": "notepadplusplus"},
        "linux": {"apt": "notepadnext", "flatpak": "com.github.dail8859.NotepadNext"},
        "binaries": ["notepad++", "notepadnext"],
        "note": "notepadnext liegt oft nicht in den Standard-APT-Quellen. Die Flatpak-ID ist der stabilere Name.",
    },
    {
        "id": "vscode",
        "names": ["visual studio code", "vscode", "code"],
        "summary_de": "Visual Studio Code gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Microsoft.VisualStudioCode", "scoop": "vscode"},
        "linux": {"apt": "code", "snap": "code"},
        "binaries": ["code"],
        "note": "Das APT-Paket code kommt aus dem Microsoft-Repo, nicht aus Ubuntu main.",
    },
    {
        "id": "vscodium",
        "names": ["vscodium", "codium"],
        "summary_de": "VSCodium ist der binärgleiche Editor ohne Microsoft-Branding, auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "VSCodium.VSCodium", "scoop": "vscodium"},
        "linux": {"apt": "codium", "flatpak": "com.vscodium.codium"},
        "binaries": ["codium"],
    },
    {
        "id": "visualstudio",
        "names": ["visual studio", "devenv"],
        "summary_de": "Visual Studio (IDE) gibt es nicht für Linux. VS Code oder VSCodium sind Workflow-Alternativen, keine Projekttyp-1:1.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.VisualStudio.2022.Community"},
        "linux": {"apt": "code", "flatpak": "com.vscodium.codium"},
        "binaries": ["devenv"],
    },
    {
        "id": "pycharm",
        "names": ["pycharm"],
        "summary_de": "PyCharm Community gibt es für Windows und Linux.",
        "equivalence": "same",
        "windows": {"winget": "JetBrains.PyCharm.Community", "scoop": "pycharm"},
        "linux": {"snap": "pycharm-community", "flatpak": "com.jetbrains.PyCharm-Community"},
        "binaries": ["pycharm", "pycharm.sh"],
    },
    {
        "id": "idea",
        "names": ["intellij idea", "intellij", "idea"],
        "summary_de": "IntelliJ IDEA gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "JetBrains.IntelliJIDEA.Community"},
        "linux": {"snap": "intellij-idea-community", "flatpak": "com.jetbrains.IntelliJ-IDEA-Community"},
        "binaries": ["idea"],
    },
    {
        "id": "sublime",
        "names": ["sublime text", "sublime", "subl"],
        "summary_de": "Sublime Text gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "SublimeHQ.SublimeText.4", "scoop": "sublime-text"},
        "linux": {"apt": "sublime-text"},
        "binaries": ["subl"],
        "note": "APT-Quelle ist das Sublime-Repo.",
    },
    {
        "id": "photoshop",
        "names": ["photoshop", "adobe photoshop"],
        "summary_de": "Photoshop läuft nicht nativ unter Linux. GIMP deckt Bildbearbeitung ab, Krita Malen und Illustration. Beides ist ein Workflow, kein PSD-1:1.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {},
        "linux_options": [
            {"role": "Bildbearbeitung", "apt": "gimp", "flatpak": "org.gimp.GIMP", "winget": "GIMP.GIMP"},
            {"role": "Malen und Illustration", "apt": "krita", "flatpak": "org.kde.krita", "winget": "KDE.Krita"},
        ],
        "binaries": ["photoshop"],
        "note": "Der Windows-Store-Eintrag von Photoshop ist kein klassischer Winget-Paketname. Auf Linux werden nur die Alternativen geplant.",
    },
    {
        "id": "illustrator",
        "names": ["illustrator", "adobe illustrator"],
        "summary_de": "Illustrator hat keinen Linux-Port. Inkscape ist die Workflow-Alternative für Vektorarbeit, kein AI-1:1.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "inkscape", "flatpak": "org.inkscape.Inkscape", "winget_counterpart": "Inkscape.Inkscape"},
        "binaries": ["illustrator", "inkscape"],
    },
    {
        "id": "premiere",
        "names": ["premiere", "premiere pro", "adobe premiere"],
        "summary_de": "Premiere Pro hat keinen Linux-Port. Kdenlive und DaVinci Resolve sind Schnitt-Alternativen mit anderem Projektformat.",
        "equivalence": "workflow",
        "windows": {},
        "linux_options": [
            {"role": "Schnitt", "apt": "kdenlive", "flatpak": "org.kde.kdenlive"},
            {"role": "Schnitt, Color", "note": "DaVinci Resolve hat einen Linux-Installer des Herstellers, kein APT-Standardpaket."},
        ],
        "binaries": ["premiere"],
    },
    {
        "id": "lightroom",
        "names": ["lightroom", "adobe lightroom"],
        "summary_de": "Lightroom hat keinen Linux-Port. darktable ist die Workflow-Alternative für Raw-Entwicklung.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "darktable", "flatpak": "org.darktable.Darktable"},
        "binaries": ["lightroom", "darktable"],
    },
    {
        "id": "aftereffects",
        "names": ["after effects", "aftereffects"],
        "summary_de": "After Effects hat keinen Linux-Port. Natron (Compositing) und Blender (Motion) sind Workflow-Alternativen.",
        "equivalence": "workflow",
        "windows": {},
        "linux_options": [
            {"role": "Node-Compositing", "apt": "natron", "flatpak": "fr.natron.Natron"},
            {"role": "3D und Motion", "apt": "blender", "winget": "BlenderFoundation.Blender"},
        ],
        "binaries": ["afterfx"],
    },
    {
        "id": "excel",
        "names": ["excel", "microsoft excel"],
        "summary_de": "Excel gibt es nicht nativ für Linux. LibreOffice Calc öffnet xlsx, ersetzt aber weder VBA noch alle Pivot-Funktionen.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.Office"},
        "linux": {"apt": "libreoffice-calc", "flatpak": "org.libreoffice.LibreOffice"},
        "binaries": ["excel", "localc"],
    },
    {
        "id": "word",
        "names": ["word", "microsoft word", "winword"],
        "summary_de": "Word gibt es nicht nativ für Linux. LibreOffice Writer ist die Workflow-Alternative für docx.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.Office"},
        "linux": {"apt": "libreoffice-writer"},
        "binaries": ["winword", "lowriter"],
    },
    {
        "id": "powerpoint",
        "names": ["powerpoint", "microsoft powerpoint", "powerpnt"],
        "summary_de": "PowerPoint gibt es nicht nativ für Linux. LibreOffice Impress ist die Workflow-Alternative.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.Office"},
        "linux": {"apt": "libreoffice-impress"},
        "binaries": ["powerpnt", "loimpress"],
    },
    {
        "id": "outlook",
        "names": ["outlook"],
        "summary_de": "Outlook (classic) hat keinen Linux-Port. Thunderbird ist die Workflow-Alternative für Mail und Kalender.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.Outlook"},
        "linux": {"apt": "thunderbird", "flatpak": "org.mozilla.Thunderbird"},
        "binaries": ["outlook", "thunderbird"],
    },
    {
        "id": "onenote",
        "names": ["onenote", "one note"],
        "summary_de": "OneNote hat keinen vollständigen Linux-Client. Joplin ist eine Workflow-Alternative für Notizen, kein Notizbuch-1:1.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "joplin", "flatpak": "net.cozic.joplin_desktop"},
        "binaries": ["onenote", "joplin"],
    },
    {
        "id": "slack",
        "names": ["slack"],
        "summary_de": "Slack gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "SlackTechnologies.Slack", "scoop": "slack"},
        "linux": {"deb": "slack-desktop", "snap": "slack", "flatpak": "com.slack.Slack"},
        "binaries": ["slack"],
    },
    {
        "id": "discord",
        "names": ["discord"],
        "summary_de": "Discord gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Discord.Discord", "scoop": "discord"},
        "linux": {"apt": "discord", "flatpak": "com.discordapp.Discord"},
        "binaries": ["discord"],
        "note": "Das APT-Paket kommt aus dem Discord-Repo oder einem Community-Paket, nicht aus Ubuntu main.",
    },
    {
        "id": "spotify",
        "names": ["spotify"],
        "summary_de": "Spotify gibt es als Client auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Spotify.Spotify", "scoop": "spotify"},
        "linux": {"snap": "spotify", "flatpak": "com.spotify.Client"},
        "binaries": ["spotify"],
    },
    {
        "id": "chrome",
        "names": ["chrome", "google chrome"],
        "summary_de": "Google Chrome gibt es für beide Systeme. Chromium ist der quelloffene Zweig, nicht dasselbe Binärpaket.",
        "equivalence": "same",
        "windows": {"winget": "Google.Chrome", "scoop": "googlechrome"},
        "linux": {"apt": "google-chrome-stable"},
        "linux_options": [{"role": "Quelloffener Zweig", "apt": "chromium-browser", "snap": "chromium"}],
        "binaries": ["google-chrome", "google-chrome-stable", "chromium"],
    },
    {
        "id": "edge",
        "names": ["edge", "microsoft edge"],
        "summary_de": "Microsoft Edge gibt es für beide Systeme.",
        "equivalence": "same",
        "windows": {"winget": "Microsoft.Edge"},
        "linux": {"apt": "microsoft-edge-stable"},
        "binaries": ["microsoft-edge", "microsoft-edge-stable"],
        "note": "APT-Quelle ist das Microsoft-Repo.",
    },
    {
        "id": "firefox",
        "names": ["firefox"],
        "summary_de": "Firefox gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Mozilla.Firefox", "scoop": "firefox"},
        "linux": {"apt": "firefox", "flatpak": "org.mozilla.firefox"},
        "binaries": ["firefox"],
    },
    {
        "id": "7zip",
        "names": ["7-zip", "7zip", "7z"],
        "summary_de": "7-Zip gibt es unter Windows als 7-Zip und unter Linux als 7zip/p7zip.",
        "equivalence": "port",
        "windows": {"winget": "7zip.7zip", "scoop": "7zip"},
        "linux": {"apt": "7zip"},
        "binaries": ["7z", "7zz"],
        "note": "Ältere Ubuntu-Versionen liefern p7zip-full statt 7zip.",
    },
    {
        "id": "winrar",
        "names": ["winrar", "rar"],
        "summary_de": "WinRAR hat keinen Linux-Port. PeaZip und unrar lesen RAR-Archive, ersetzen die Shell-Integration nicht 1:1.",
        "equivalence": "workflow",
        "windows": {"winget": "RARLab.WinRAR"},
        "linux": {"apt": "unar", "flatpak": "io.github.peazip.PeaZip"},
        "binaries": ["winrar", "unrar"],
    },
    {
        "id": "paintdotnet",
        "names": ["paint.net", "paintdotnet"],
        "summary_de": "paint.net gibt es nicht für Linux. Pinta ist eine nahe Workflow-Alternative, Krita die schwerere.",
        "equivalence": "workflow",
        "windows": {"winget": "dotPDN.PaintDotNet"},
        "linux": {"apt": "pinta", "flatpak": "com.github.PintaProject.Pinta"},
        "binaries": ["paintdotnet", "pinta"],
    },
    {
        "id": "sharex",
        "names": ["sharex"],
        "summary_de": "ShareX ist Windows-only. Flameshot übernimmt Screenshot und Annotation, nicht den Uploader-Baukasten.",
        "equivalence": "workflow",
        "windows": {"winget": "ShareX.ShareX", "scoop": "sharex"},
        "linux": {"apt": "flameshot", "flatpak": "org.flameshot.Flameshot"},
        "binaries": ["sharex", "flameshot"],
    },
    {
        "id": "everything",
        "names": ["everything", "voidtools"],
        "summary_de": "Everything ist eine NTFS-Dateisuche ohne Linux-Port. FSearch ist die Workflow-Alternative.",
        "equivalence": "workflow",
        "windows": {"winget": "voidtools.Everything"},
        "linux": {"apt": "fsearch"},
        "binaries": ["everything", "fsearch"],
    },
    {
        "id": "windowsterminal",
        "names": ["windows terminal", "windowsterminal", "wt"],
        "summary_de": "Windows Terminal ist an die Windows-Konsole gebunden. GNOME Terminal, Kitty oder Alacritty sind Workflow-Alternativen.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.WindowsTerminal"},
        "linux_options": [
            {"role": "Desktop-Standard", "apt": "gnome-terminal"},
            {"role": "GPU-Terminal", "apt": "kitty"},
            {"role": "Minimal", "apt": "alacritty"},
        ],
        "binaries": ["wt", "gnome-terminal", "kitty"],
    },
    {
        "id": "putty",
        "names": ["putty"],
        "summary_de": "PuTTY gibt es auch für Linux. OpenSSH ist die übliche native Alternative.",
        "equivalence": "same",
        "windows": {"winget": "PuTTY.PuTTY", "scoop": "putty"},
        "linux": {"apt": "putty"},
        "linux_options": [{"role": "Native SSH", "apt": "openssh-client"}],
        "binaries": ["putty", "ssh"],
    },
    {
        "id": "filezilla",
        "names": ["filezilla"],
        "summary_de": "FileZilla gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "FileZilla.FileZilla", "scoop": "filezilla"},
        "linux": {"apt": "filezilla", "flatpak": "org.filezillaproject.Filezilla"},
        "binaries": ["filezilla"],
    },
    {
        "id": "winscp",
        "names": ["winscp"],
        "summary_de": "WinSCP ist Windows-only. FileZilla oder das OpenSSH-sftp sind die Workflow-Alternativen.",
        "equivalence": "workflow",
        "windows": {"winget": "WinSCP.WinSCP"},
        "linux": {"apt": "filezilla"},
        "binaries": ["winscp"],
    },
    {
        "id": "vlc",
        "names": ["vlc"],
        "summary_de": "VLC gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "VideoLAN.VLC", "scoop": "vlc"},
        "linux": {"apt": "vlc", "snap": "vlc", "flatpak": "org.videolan.VLC"},
        "binaries": ["vlc"],
    },
    {
        "id": "obs",
        "names": ["obs", "obs studio"],
        "summary_de": "OBS Studio gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "OBSProject.OBSStudio", "scoop": "obs-studio"},
        "linux": {"apt": "obs-studio", "flatpak": "com.obsproject.Studio"},
        "binaries": ["obs"],
    },
    {
        "id": "teams",
        "names": ["teams", "microsoft teams"],
        "summary_de": "Das neue Teams ist nicht dasselbe wie teams-for-linux. Letzteres ist ein Community-Client und kein 1:1.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.Teams"},
        "linux": {"flatpak": "com.github.IsmaelMartinez.teams_for_linux"},
        "binaries": ["teams"],
    },
    {
        "id": "zoom",
        "names": ["zoom"],
        "summary_de": "Zoom gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Zoom.Zoom", "scoop": "zoom"},
        "linux": {"apt": "zoom", "flatpak": "us.zoom.Zoom"},
        "binaries": ["zoom"],
        "note": "Das DEB kommt von Zoom, nicht aus Ubuntu main.",
    },
    {
        "id": "docker",
        "names": ["docker desktop", "docker"],
        "summary_de": "Docker Engine gibt es auf beiden Systemen. Docker Desktop ist eine Windows/Mac-Hülle und nicht identisch mit docker.io.",
        "equivalence": "workflow",
        "windows": {"winget": "Docker.DockerDesktop"},
        "linux": {"apt": "docker.io"},
        "binaries": ["docker"],
    },
    {
        "id": "git",
        "names": ["git"],
        "summary_de": "Git gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Git.Git", "scoop": "git"},
        "linux": {"apt": "git"},
        "binaries": ["git"],
    },
    {
        "id": "nodejs",
        "names": ["node", "nodejs", "node.js"],
        "summary_de": "Node.js gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "OpenJS.NodeJS", "scoop": "nodejs"},
        "linux": {"apt": "nodejs"},
        "binaries": ["node", "nodejs"],
    },
    {
        "id": "python",
        "names": ["python", "python3"],
        "summary_de": "CPython gibt es auf beiden Systemen. Unter Linux ist das Paket python3.",
        "equivalence": "same",
        "windows": {"winget": "Python.Python.3.12", "scoop": "python"},
        "linux": {"apt": "python3"},
        "binaries": ["python", "python3"],
    },
    {
        "id": "postman",
        "names": ["postman"],
        "summary_de": "Postman gibt es auf beiden Systemen. Insomnia ist eine zweite Workflow-Option.",
        "equivalence": "same",
        "windows": {"winget": "Postman.Postman"},
        "linux": {"snap": "postman", "flatpak": "com.getpostman.Postman"},
        "linux_options": [{"role": "Alternative", "flatpak": "rest.insomnia.Insomnia"}],
        "binaries": ["postman"],
    },
    {
        "id": "wireshark",
        "names": ["wireshark"],
        "summary_de": "Wireshark gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "WiresharkFoundation.Wireshark", "scoop": "wireshark"},
        "linux": {"apt": "wireshark"},
        "binaries": ["wireshark"],
    },
    {
        "id": "virtualbox",
        "names": ["virtualbox", "vbox"],
        "summary_de": "VirtualBox gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Oracle.VirtualBox"},
        "linux": {"apt": "virtualbox"},
        "binaries": ["virtualbox", "VBoxManage"],
    },
    {
        "id": "vmware",
        "names": ["vmware", "vmware workstation"],
        "summary_de": "VMware Workstation hat keinen frei äquivalenten Linux-Hypervisor. virt-manager/QEMU ist eine Workflow-Alternative, kein VMX-1:1.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "virt-manager"},
        "binaries": ["vmware", "virt-manager"],
    },
    {
        "id": "autohotkey",
        "names": ["autohotkey", "ahk"],
        "summary_de": "AutoHotkey ist Windows-only. AutoKey bildet Textbausteine unter Linux ab, nicht das AHK-Objektmodell.",
        "equivalence": "workflow",
        "windows": {"winget": "AutoHotkey.AutoHotkey"},
        "linux": {"apt": "autokey-gtk"},
        "binaries": ["autohotkey", "autokey-gtk"],
    },
    {
        "id": "keepass",
        "names": ["keepass", "keepassxc"],
        "summary_de": "KeePassXC liest kdbx auf beiden Systemen. KeePass 2.x (classic) ist nicht dasselbe Binärpaket.",
        "equivalence": "port",
        "windows": {"winget": "KeePassXCTeam.KeePassXC", "scoop": "keepassxc"},
        "linux": {"apt": "keepassxc", "flatpak": "org.keepassxc.KeePassXC"},
        "binaries": ["keepassxc"],
    },
    {
        "id": "bitwarden",
        "names": ["bitwarden"],
        "summary_de": "Bitwarden gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Bitwarden.Bitwarden"},
        "linux": {"snap": "bitwarden", "flatpak": "com.bitwarden.desktop"},
        "binaries": ["bitwarden"],
    },
    {
        "id": "telegram",
        "names": ["telegram"],
        "summary_de": "Telegram Desktop gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Telegram.TelegramDesktop"},
        "linux": {"apt": "telegram-desktop", "flatpak": "org.telegram.desktop"},
        "binaries": ["telegram-desktop"],
    },
    {
        "id": "signal",
        "names": ["signal"],
        "summary_de": "Signal Desktop gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "OpenWhisperSystems.Signal"},
        "linux": {"apt": "signal-desktop"},
        "binaries": ["signal-desktop"],
        "note": "APT-Quelle ist das Signal-Repo.",
    },
    {
        "id": "audacity",
        "names": ["audacity"],
        "summary_de": "Audacity gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Audacity.Audacity", "scoop": "audacity"},
        "linux": {"apt": "audacity", "flatpak": "org.audacityteam.Audacity"},
        "binaries": ["audacity"],
    },
    {
        "id": "blender",
        "names": ["blender"],
        "summary_de": "Blender gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "BlenderFoundation.Blender", "scoop": "blender"},
        "linux": {"apt": "blender", "snap": "blender", "flatpak": "org.blender.Blender"},
        "binaries": ["blender"],
    },
    {
        "id": "steam",
        "names": ["steam"],
        "summary_de": "Steam gibt es auf beiden Systemen. Proton ist eine Linux-Laufzeit, kein Windows-Installer.",
        "equivalence": "same",
        "windows": {"winget": "Valve.Steam"},
        "linux": {"apt": "steam"},
        "binaries": ["steam"],
        "note": "Unter Ubuntu liegt steam in multiverse bzw. im Valve-Repo.",
    },
    {
        "id": "epic",
        "names": ["epic games", "epic", "epic games launcher"],
        "summary_de": "Der Epic Games Launcher hat keinen nativen Linux-Port. Heroic ist ein Community-Launcher und kein 1:1.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"flatpak": "com.heroicgameslauncher.hgl"},
        "binaries": ["heroic"],
    },
    {
        "id": "qbittorrent",
        "names": ["qbittorrent"],
        "summary_de": "qBittorrent gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "qBittorrent.qBittorrent", "scoop": "qbittorrent"},
        "linux": {"apt": "qbittorrent", "flatpak": "org.qbittorrent.qBittorrent"},
        "binaries": ["qbittorrent"],
    },
    {
        "id": "utorrent",
        "names": ["utorrent", "bittorrent"],
        "summary_de": "µTorrent ist Windows-lastig. Transmission oder qBittorrent sind die Workflow-Alternativen.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "transmission"},
        "binaries": ["utorrent", "transmission-gtk"],
    },
    {
        "id": "rufus",
        "names": ["rufus"],
        "summary_de": "Rufus schreibt Windows-Installationsmedien und hat keinen Linux-Port. Ventoy ist eine Workflow-Alternative, kein Rufus-1:1.",
        "equivalence": "workflow",
        "windows": {"winget": "Rufus.Rufus"},
        "linux": {"apt": "ventoy"},
        "binaries": ["rufus"],
        "note": "ventoy ist nicht in jeder Ubuntu-Version in den Standardquellen.",
    },
    {
        "id": "etcher",
        "names": ["etcher", "balena etcher", "balenaetcher"],
        "summary_de": "balenaEtcher gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Balena.Etcher"},
        "linux": {"apt": "balena-etcher-electron"},
        "binaries": ["balena-etcher"],
        "note": "Das DEB kommt von balena, nicht aus Ubuntu main.",
    },
    {
        "id": "windirstat",
        "names": ["windirstat"],
        "summary_de": "WinDirStat ist Windows-only. QDirStat und ncdu sind die Workflow-Alternativen.",
        "equivalence": "workflow",
        "windows": {"winget": "WinDirStat.WinDirStat"},
        "linux_options": [
            {"role": "GUI", "apt": "qdirstat"},
            {"role": "Terminal", "apt": "ncdu"},
        ],
        "binaries": ["windirstat", "qdirstat", "ncdu"],
    },
    {
        "id": "treesize",
        "names": ["treesize"],
        "summary_de": "TreeSize ist Windows-only. Baobab (GNOME Disk Usage) ist die Workflow-Alternative.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "baobab"},
        "binaries": ["baobab"],
    },
    {
        "id": "procexp",
        "names": ["process explorer", "procexp"],
        "summary_de": "Process Explorer ist ein Sysinternals-Werkzeug. htop zeigt Prozesse, ersetzt Handle-Suche und VirusTotal-Anbindung nicht.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "htop"},
        "binaries": ["procexp", "htop"],
    },
    {
        "id": "hwmonitor",
        "names": ["hwmonitor", "hwmonitor"],
        "summary_de": "HWMonitor hat keinen Linux-Port. lm-sensors und psensor lesen Sensoren, wenn der Kernel sie liefert.",
        "equivalence": "workflow",
        "windows": {"winget": "CPUID.HWMonitor"},
        "linux": {"apt": "psensor"},
        "linux_options": [{"role": "Sensoren", "apt": "lm-sensors"}],
        "binaries": ["hwmonitor", "psensor"],
    },
    {
        "id": "crystaldiskinfo",
        "names": ["crystaldiskinfo"],
        "summary_de": "CrystalDiskInfo ist Windows-only. smartmontools/gsmartcontrol lesen SMART, wenn das Gerät es hergibt.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "gsmartcontrol"},
        "linux_options": [{"role": "CLI", "apt": "smartmontools"}],
        "binaries": ["gsmartcontrol", "smartctl"],
    },
    {
        "id": "cpuz",
        "names": ["cpu-z", "cpuz"],
        "summary_de": "CPU-Z ist Windows-only. CPU-X ist eine Workflow-Alternative und kein Validierungs-1:1.",
        "equivalence": "workflow",
        "windows": {"winget": "CPUID.CPU-Z"},
        "linux": {"apt": "cpu-x"},
        "binaries": ["cpuz", "cpu-x"],
    },
    {
        "id": "nvidiacpl",
        "names": ["nvidia control panel", "nvidia-settings"],
        "summary_de": "Die NVIDIA-Systemsteuerung unter Windows und nvidia-settings unter Linux steuern denselben Hersteller, aber nicht dieselben Dialoge.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "nvidia-settings"},
        "binaries": ["nvidia-settings"],
    },
    {
        "id": "afterburner",
        "names": ["msi afterburner", "afterburner"],
        "summary_de": "MSI Afterburner ist Windows-only. CoreCtrl (AMD) und LACT sind Workflow-Alternativen. CrossOS wendet damit keine Takte an.",
        "equivalence": "workflow",
        "windows": {},
        "linux_options": [
            {"role": "AMD", "apt": "corectrl"},
            {"role": "Herstellerübergreifend", "note": "LACT wird nicht blind installiert; nur als Hinweis."},
        ],
        "binaries": ["corectrl"],
    },
    {
        "id": "notepad",
        "names": ["notepad", "notepad.exe"],
        "summary_de": "Der Windows-Editor hat keinen Port. gnome-text-editor ist der schlichte Workflow-Ersatz.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "gnome-text-editor"},
        "binaries": ["notepad", "gnome-text-editor"],
    },
    {
        "id": "irfanview",
        "names": ["irfanview"],
        "summary_de": "IrfanView ist Windows-only. Gwenview ist eine Workflow-Alternative für die Bildanzeige.",
        "equivalence": "workflow",
        "windows": {"winget": "IrfanSkiljan.IrfanView"},
        "linux": {"apt": "gwenview"},
        "binaries": ["i_view64", "gwenview"],
    },
    {
        "id": "dropbox",
        "names": ["dropbox"],
        "summary_de": "Dropbox gibt es auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Dropbox.Dropbox"},
        "linux": {"apt": "dropbox"},
        "binaries": ["dropbox"],
        "note": "Das DEB kommt von Dropbox.",
    },
    {
        "id": "onedrive",
        "names": ["onedrive"],
        "summary_de": "Der OneDrive-Client ist kein Linux-Standard. rclone kann das Konto einbinden und ist kein Explorer-1:1.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "rclone"},
        "binaries": ["onedrive", "rclone"],
    },
    {
        "id": "acrobat",
        "names": ["acrobat", "adobe acrobat"],
        "summary_de": "Adobe Acrobat gibt es nicht nativ für Linux. Okular und Evince zeigen PDF, ersetzen Formular- und Signaturfunktionen nicht.",
        "equivalence": "workflow",
        "windows": {"winget": "Adobe.Acrobat.Reader.64-bit"},
        "linux_options": [
            {"role": "KDE", "apt": "okular"},
            {"role": "GNOME", "apt": "evince"},
        ],
        "binaries": ["acrobat", "okular", "evince"],
    },
    {
        "id": "powertoys",
        "names": ["powertoys", "microsoft powertoys"],
        "summary_de": "PowerToys ist Windows-only. CopyQ und gTile decken nur Ausschnitte (Zwischenablage, Kacheln) ab.",
        "equivalence": "workflow",
        "windows": {"winget": "Microsoft.PowerToys"},
        "linux_options": [
            {"role": "Zwischenablage", "apt": "copyq"},
            {"role": "Fensterkacheln", "note": "gTile ist eine GNOME-Shell-Erweiterung, kein APT-Standardpaket."},
        ],
        "binaries": ["powertoys", "copyq"],
    },
    {
        "id": "greenshot",
        "names": ["greenshot"],
        "summary_de": "Greenshot ist Windows-only. Flameshot ist die Workflow-Alternative.",
        "equivalence": "workflow",
        "windows": {"winget": "Greenshot.Greenshot"},
        "linux": {"apt": "flameshot"},
        "binaries": ["greenshot", "flameshot"],
    },
    {
        "id": "skype",
        "names": ["skype"],
        "summary_de": "Skype gibt es als Client auf beiden Systemen.",
        "equivalence": "same",
        "windows": {"winget": "Microsoft.Skype"},
        "linux": {"snap": "skype"},
        "binaries": ["skype"],
    },
    {
        "id": "whatsapp",
        "names": ["whatsapp"],
        "summary_de": "WhatsApp Desktop gibt es offiziell für Windows. Unter Linux ist der Flatpak-Client ein Wrapper und kein 1:1 der Store-App.",
        "equivalence": "workflow",
        "windows": {"winget": "WhatsApp.WhatsApp"},
        "linux": {"flatpak": "com.rtosta.zapzap"},
        "binaries": ["whatsapp"],
        "note": "ZapZap ist ein inoffizieller Client.",
    },
    {
        "id": "ccleaner",
        "names": ["ccleaner"],
        "summary_de": "CCleaner ist Windows-only. BleachBit ist eine Workflow-Alternative. CrossOS führt keine Putzläufe aus.",
        "equivalence": "workflow",
        "windows": {},
        "linux": {"apt": "bleachbit"},
        "binaries": ["ccleaner", "bleachbit"],
    },
    {
        "id": "malwarebytes",
        "names": ["malwarebytes"],
        "summary_de": "Malwarebytes hat keinen gleichwertigen Linux-Port. ClamAV ist ein anderer Scanner, kein Echtzeit-1:1.",
        "equivalence": "workflow",
        "windows": {"winget": "Malwarebytes.Malwarebytes"},
        "linux": {"apt": "clamav"},
        "binaries": ["mbam", "clamscan"],
    },
]


def _index() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for app in CATALOG:
        index[app["id"]] = app
        for name in app["names"]:
            index[name.casefold()] = app
    return index


@lru_cache(maxsize=1)
def catalog_index() -> dict[str, dict]:
    return _index()


def list_catalog() -> list[dict]:
    return [
        {
            "id": app["id"],
            "names": app["names"],
            "equivalence": app["equivalence"],
            "summary_de": app["summary_de"],
        }
        for app in CATALOG
    ]


def resolve_app(name: str) -> dict:
    found = catalog_index().get(name.casefold())
    if not found:
        raise SafetyError(f"Anwendung nicht im Katalog: {name}")
    return found


def _package_plans(bridge: PackageBridge, side: dict, *, prefer: str) -> list[dict]:
    plans = []
    order = {
        "linux": ["apt", "flatpak", "snap"],
        "windows": ["winget", "scoop"],
    }[prefer]
    for manager in order:
        package = side.get(manager)
        if not package:
            continue
        plans.append(bridge.plan(manager, [package], "install"))
    return plans


def _option_plans(bridge: PackageBridge, options: list[dict], *, prefer: str) -> list[dict]:
    built = []
    for option in options:
        entry = {"role": option.get("role", ""), "note": option.get("note"), "plans": []}
        side = {key: value for key, value in option.items() if key in {"apt", "flatpak", "snap", "winget", "scoop"}}
        entry["plans"] = _package_plans(bridge, side, prefer=prefer)
        built.append(entry)
    return built


def plan_apps(names: list[str], *, target_os: str, detect: bool = False) -> dict:
    if target_os not in {"linux", "windows"}:
        raise SafetyError("Ziel für den App-Plan muss linux oder windows sein.")
    bridge = PackageBridge()
    items = []
    for name in names:
        app = resolve_app(name)
        prefer = target_os
        source_side = app.get("windows" if target_os == "linux" else "linux", {})
        target_side = app.get(target_os, {})
        items.append(
            {
                "id": app["id"],
                "query": name,
                "equivalence": app["equivalence"],
                "summary_de": app["summary_de"],
                "note": app.get("note"),
                "installed_here": _installed(app) if detect else None,
                "target_plans": _package_plans(bridge, target_side, prefer=prefer),
                "alternatives": _option_plans(bridge, app.get("linux_options" if target_os == "linux" else "windows_options", []), prefer=prefer),
                "source_hint": {key: value for key, value in source_side.items() if isinstance(value, str)},
            }
        )
    return {
        "target_os": target_os,
        "managers": bridge.detect(),
        "apps": items,
        "executed": False,
        "dry_run": True,
    }


def _installed(app: dict) -> dict:
    binaries = []
    for binary in app.get("binaries", []):
        binaries.append({"binary": binary, "present": shutil.which(binary) is not None})
    packages = []
    apt_names = []
    if "apt" in app.get("linux", {}):
        apt_names.append(app["linux"]["apt"])
    for option in app.get("linux_options", []):
        if "apt" in option:
            apt_names.append(option["apt"])
    if shutil.which("dpkg") and apt_names:
        for package in apt_names:
            packages.append(_dpkg_status(package))
    return {"binaries": binaries, "dpkg": packages}


def _dpkg_status(package: str) -> dict:
    from crossos.safety import validate_package_name

    clean = validate_package_name(package)
    completed = subprocess.run(
        ["dpkg-query", "-W", "-f", "${db:Status-Status}", clean],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    status = (completed.stdout or "").strip()
    return {"package": clean, "status": status or "unknown", "installed": status == "installed"}
