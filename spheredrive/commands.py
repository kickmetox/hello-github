"""Aufbau der Windows-Befehle. Die Funktionen führen nichts aus."""

from __future__ import annotations

import os
import re

PROFILE_BEGIN = "# --- SphereDrive BEGIN ---"
PROFILE_END = "# --- SphereDrive END ---"
TASK_NAME = r"SphereDrive\RestoreMappings"

DOS_DEVICES = r"SYSTEM\CurrentControlSet\Control\Session Manager\DOS Devices"
POLICIES_SYSTEM = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPMODEL_UNLOCK = r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
FOLDER_DESC = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions"
FOLDER_DESC_WOW = r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions"
BITBUCKET = r"Software\Microsoft\Windows\CurrentVersion\Explorer\BitBucket\KnownFolder"
BITBUCKET_WOW = r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Explorer\BitBucket\KnownFolder"


def normalize_letter(value: str) -> str | None:
    text = (value or "").strip().rstrip(":").upper()
    if len(text) == 1 and "A" <= text <= "Z":
        return text
    return None


def _windows_parts(path: str) -> tuple[str, list[str]]:
    """Zerlegt einen Windows-Pfad unabhängig vom Betriebssystem des Prozesses."""
    raw = path.strip().strip('"').replace("/", "\\")
    unc = raw.startswith("\\\\")
    if unc:
        raw = raw[2:]
    stack: list[str] = []
    for part in raw.split("\\"):
        if part in ("", "."):
            continue
        if part == ".." and stack:
            stack.pop()
            continue
        if part == "..":
            continue
        stack.append(part)
    if unc:
        kind = "unc"
    elif stack and len(stack[0]) == 2 and stack[0][1] == ":":
        kind = "drive"
    else:
        kind = "rel"
    return kind, stack


def _windows_join(kind: str, parts: list[str]) -> str:
    if kind == "unc":
        return "\\\\" + "\\".join(parts)
    if kind == "drive" and parts:
        drive, tail = parts[0], parts[1:]
        if not tail:
            return drive + "\\"
        return drive + "\\" + "\\".join(tail)
    return "\\".join(parts)


def norm_path(path: str) -> str:
    kind, parts = _windows_parts(path)
    return _windows_join(kind, parts).casefold()


def join_path(parent: str, name: str) -> str:
    """Hängt einen Ordnernamen an einen Windows-Pfad, auch unterhalb von C:\\."""
    kind, parts = _windows_parts(parent)
    return _windows_join(kind, parts + [name])


def map_through_subst(path: str, subst: dict[str, str]) -> str:
    """Ersetzt einen Subst-Buchstaben durch den Zielordner, Unterordner bleiben erhalten."""
    kind, parts = _windows_parts(path)
    if kind != "drive" or not parts:
        return _windows_join(kind, parts) if parts else path.strip()
    letter = parts[0][0].upper()
    target = subst.get(letter)
    if not target:
        return _windows_join(kind, parts)
    target_kind, target_parts = _windows_parts(target)
    return _windows_join(target_kind, target_parts + parts[1:])


def parent_dir(path: str) -> str:
    kind, parts = _windows_parts(path)
    if len(parts) <= 1:
        return ""
    return _windows_join(kind, parts[:-1])


def dos_device_value(path: str) -> str:
    """Kernel-Pfad für HKLM\\...\\DOS Devices, z. B. \\??\\C:\\Projekte."""
    kind, parts = _windows_parts(path)
    return "\\??\\" + _windows_join(kind, parts)


def subst_create(letter: str, path: str) -> list[str]:
    return ["subst", f"{letter}:", path]


def subst_delete(letter: str) -> list[str]:
    return ["subst", f"{letter}:", "/D"]


def subst_list() -> list[str]:
    return ["subst"]


def quote_cmd(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def mklink_command(kind: str, link: str, target: str) -> list[str]:
    flags = {
        "junction": "/J",
        "symlink_dir": "/D",
        "symlink_file": "",
        "hardlink": "/H",
    }
    if kind not in flags:
        raise ValueError(f"Unbekannte Verknüpfungsart: {kind}")
    flag = flags[kind]
    pieces = ["mklink"]
    if flag:
        pieces.append(flag)
    pieces.append(quote_cmd(link))
    pieces.append(quote_cmd(target))
    return ["cmd", "/c", " ".join(pieces)]


def rmdir_command(link: str) -> list[str]:
    return ["cmd", "/c", f"rmdir {quote_cmd(link)}"]


def del_command(link: str) -> list[str]:
    return ["cmd", "/c", f"del /f {quote_cmd(link)}"]


def net_use_list() -> list[str]:
    return ["net", "use"]


def net_use_connect(spec_letter: str, remote: str, user: str, password: str, persistent: bool) -> list[str]:
    args = ["net", "use", f"{spec_letter}:", remote]
    if user:
        args.append("/user:" + user)
        if password:
            args.append(password)
        else:
            args.append("/savecred")
    args.append("/persistent:yes" if persistent else "/persistent:no")
    return args


def net_use_delete(letter: str) -> list[str]:
    return ["net", "use", f"{letter}:", "/delete"]


def net_share_list() -> list[str]:
    return ["net", "share"]


def net_share_create(name: str, path: str, permission: str, principal: str) -> list[str]:
    grant = permission if permission in {"READ", "CHANGE", "FULL"} else "READ"
    args = ["net", "share", f"{name}={path}"]
    if principal:
        args.append(f"/GRANT:{principal},{grant}")
    return args


def net_share_delete(name: str) -> list[str]:
    return ["net", "share", name, "/delete", "/y"]


def mountvol_list() -> list[str]:
    return ["mountvol"]


def mountvol_assign(target: str, volume: str) -> list[str]:
    return ["mountvol", target, volume]


def mountvol_remove(target: str) -> list[str]:
    return ["mountvol", target, "/D"]


def drive_icon_key(letter: str, leaf: str) -> str:
    return rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{letter}\{leaf}"


def icon_registry_value(path: str) -> str:
    name = os.path.basename(path)
    if "," in name:
        return path
    return path + ",0"


def mountpoints2_key(unc: str) -> str:
    raw = unc.strip().replace("/", "\\")
    if raw.startswith("\\\\"):
        raw = raw[2:]
    raw = raw.rstrip("\\")
    encoded = "##" + raw.replace("\\", "#")
    return r"Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\\" + encoded


def network_key(letter: str) -> str:
    return rf"Network\{letter}"


def autostart_command(pythonw: str, script: str) -> str:
    return f'"{pythonw}" "{script}" --restore'


def _ps_quote(value: str) -> str:
    return value.replace("'", "''")


def ps_list_volumes_script() -> str:
    return (
        "Get-CimInstance Win32_Volume | ForEach-Object { "
        "[PSCustomObject]@{ DeviceID = $_.DeviceID; DriveLetter = $_.DriveLetter; "
        "Label = $_.Label; FileSystem = $_.FileSystem; Capacity = $_.Capacity; "
        "FreeSpace = $_.FreeSpace } } | ConvertTo-Json -Compress"
    )


def ps_list_drives_script() -> str:
    return (
        "Get-PSDrive | ForEach-Object { [PSCustomObject]@{ Name = $_.Name; "
        "Provider = $_.Provider.Name; Root = [string]$_.Root } } | ConvertTo-Json -Compress"
    )


def ps_new_drive_script(name: str, provider: str, root: str, persist: bool) -> str:
    flag = " -Persist" if persist else ""
    return (
        f"New-PSDrive -Name '{_ps_quote(name)}' -PSProvider '{_ps_quote(provider)}' "
        f"-Root '{_ps_quote(root)}' -Scope Global{flag} | Out-Null"
    )


def ps_remove_drive_script(name: str) -> str:
    return f"Remove-PSDrive -Name '{_ps_quote(name)}' -Force -ErrorAction Stop"


def ps_profile_line(name: str, provider: str, root: str) -> str:
    return (
        f"if (-not (Get-PSDrive -Name '{_ps_quote(name)}' -ErrorAction SilentlyContinue)) "
        f"{{ New-PSDrive -Name '{_ps_quote(name)}' -PSProvider '{_ps_quote(provider)}' "
        f"-Root '{_ps_quote(root)}' -Scope Global -ErrorAction SilentlyContinue | Out-Null }}"
    )


def render_profile_block(drives: list[dict]) -> str:
    selected = [item for item in drives if item.get("profile")]
    if not selected:
        return ""
    lines = [
        PROFILE_BEGIN,
        "# Von SphereDrive verwaltet. Änderungen in diesem Block werden überschrieben.",
    ]
    for item in selected:
        lines.append(ps_profile_line(item["name"], item["provider"], item["root"]))
    lines.append(PROFILE_END)
    return "\n".join(lines) + "\n"


def replace_marked_block(text: str, block: str) -> str:
    pattern = re.compile(
        re.escape(PROFILE_BEGIN) + r".*?" + re.escape(PROFILE_END) + r"\r?\n?",
        re.DOTALL,
    )
    if PROFILE_BEGIN in text:
        updated = pattern.sub(lambda _match: block, text, count=1)
        return updated
    if not block:
        return text
    if text and not text.endswith("\n"):
        text += "\n"
    if text and not text.endswith("\n\n"):
        text += "\n"
    return text + block


def ps_scan_reparse_script(folder: str) -> str:
    return (
        f"$root = '{_ps_quote(folder)}'\n"
        "Get-ChildItem -LiteralPath $root -Force -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint } | "
        "ForEach-Object { $targets = @($_.Target); "
        "[PSCustomObject]@{ Link = $_.FullName; LinkType = [string]$_.LinkType; "
        "Attributes = [int]$_.Attributes; Target = ($targets -join ' | ') } } | "
        "ConvertTo-Json -Compress"
    )


def normalize_volume_id(value: str) -> str | None:
    text = (value or "").strip()
    match = re.search(r"\{([0-9A-Fa-f-]{36})\}", text)
    if match:
        guid = match.group(1)
    elif re.fullmatch(r"[0-9A-Fa-f-]{36}", text):
        guid = text
    else:
        return None
    return "\\\\?\\Volume{" + guid + "}\\"


def is_drive_target(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]:?", (value or "").strip()))


def normalize_mount_target(value: str) -> str | None:
    text = (value or "").strip().strip('"')
    if not text:
        return None
    if is_drive_target(text):
        return normalize_letter(text) + ":"
    return os.path.normpath(text)


def suggest_letter(used: set[str]) -> str:
    for letter in "PQRSTUVWXYZDEFGHIJKLMNO":
        if letter not in used:
            return letter
    return "Z"


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def task_xml(command: str, arguments: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>SphereDrive stellt virtuelle Laufwerke für erhöhte Prozesse wieder her.</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{xml_escape(command)}</Command>
      <Arguments>{xml_escape(arguments)}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def share_name_ok(name: str) -> bool:
    if not name or name.endswith("$"):
        return False
    return re.fullmatch(r"[^\\/:*?\"<>|]{1,80}", name) is not None


def ps_name_ok(name: str) -> bool:
    return re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,30}", name or "") is not None


def build_unc(computer: str, share: str) -> str | None:
    host = computer.strip().lstrip("\\").strip()
    name = share.strip().strip("\\")
    if not host or not name or any(char in name for char in "\\/:*?\"<>|"):
        return None
    return f"\\\\{host}\\{name}"


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
