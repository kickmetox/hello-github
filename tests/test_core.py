"""Prüft Befehlaufbau, Parser und die Fachlogik gegen die Vorschau, ohne Windows anzufassen."""

from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

from spheredrive.commands import (
    join_path,
    map_through_subst,
    BITBUCKET,
    DOS_DEVICES,
    FOLDER_DESC,
    POLICIES_SYSTEM,
    dos_device_value,
    drive_icon_key,
    mklink_command,
    net_use_connect,
    norm_path,
    parent_dir,
    ps_new_drive_script,
    render_profile_block,
    replace_marked_block,
    subst_create,
)
from spheredrive.catalog import DESCRIPTION, FEATURES
from spheredrive.host import PreviewHost, system_caption
from spheredrive.models import LinkSpec, MountSpec, NetSpec, PsSpec, ShareSpec, SubstSpec
from spheredrive.parsers import parse_mountvol, parse_net_share, parse_net_use, parse_subst
from spheredrive.paths import (
    bundled_restore,
    choose_icon,
    ensure_work_dir,
    format_launch,
    place_logo,
    publish_to,
    restore_launch,
)
from spheredrive.service import SphereService


def service(tmp: Path, *, admin: bool = False, strict: bool = True) -> tuple[SphereService, PreviewHost]:
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    host = PreviewHost(root=tmp / "home")
    host.strict_paths = strict
    host.set_admin(admin)
    return SphereService(host=host, store_path=tmp / "config.json"), host


def allow_dir(host: PreviewHost, path: str) -> None:
    host.dirs.add(norm_path(path))


class CommandTests(unittest.TestCase):
    def test_dos_device_and_parent_are_windows_paths_on_any_os(self) -> None:
        self.assertEqual(dos_device_value(r"C:\Projekte\."), r"\??\C:\Projekte")
        self.assertEqual(dos_device_value("C:/Projekte/"), r"\??\C:\Projekte")
        self.assertEqual(dos_device_value("C:\\"), "\\??\\C:\\")
        self.assertEqual(parent_dir(r"C:\Links\App"), r"C:\Links")
        self.assertEqual(norm_path("C:/Projekte"), norm_path(r"C:\Projekte"))

    def test_command_shapes(self) -> None:
        self.assertEqual(subst_create("P", r"C:\Projekte"), ["subst", "P:", r"C:\Projekte"])
        net = net_use_connect("Z", r"\\nas\archiv", "ada", "secret", True)
        self.assertEqual(net[:4], ["net", "use", "Z:", r"\\nas\archiv"])
        self.assertIn("/user:ada", net)
        self.assertIn("secret", net)
        self.assertIn("/persistent:yes", net)
        command = mklink_command("junction", r"C:\Links\App", r"D:\Daten")
        self.assertEqual(command[0], "cmd")
        self.assertIn("/J", command[2])
        script = ps_new_drive_script("Projekte", "FileSystem", r"C:\Projekte", False)
        self.assertIn("-Name 'Projekte'", script)
        self.assertNotIn("-Persist", script)


class ParserTests(unittest.TestCase):
    def test_subst_net_share_and_mountvol(self) -> None:
        subst = parse_subst("P:\\: => C:\\Projekte\nZ:\\: => D:\\Daten\n")
        self.assertEqual([(item.letter, item.path) for item in subst], [("P", r"C:\Projekte"), ("Z", r"D:\Daten")])
        net = parse_net_use(
            "\n".join(
                [
                    "Status       Lokal     Remote                    Netzwerk",
                    "-------------------------------------------------------------------------------",
                    r"OK           Z:        \\nas\archiv              Microsoft Windows Network",
                    r"Nicht verfügbar  Y:        \\nas\weg              Microsoft Windows Network",
                ]
            )
        )
        self.assertEqual(net[0].letter, "Z")
        self.assertEqual(net[0].remote, r"\\nas\archiv")
        self.assertEqual(net[1].letter, "Y")
        self.assertIn("verfügbar", net[1].status)
        shares = parse_net_share("Projekte       C:\\Projekte                     Projektordner\n")
        self.assertEqual(shares[0].name, "Projekte")
        self.assertEqual(shares[0].path, r"C:\Projekte")
        volumes = parse_mountvol(
            "\n".join(
                [
                    "    \\\\?\\Volume{11111111-1111-1111-1111-111111111111}\\",
                    "        C:\\",
                    "    \\\\?\\Volume{22222222-2222-2222-2222-222222222222}\\",
                    "        *** KEINE BEREITSTELLUNGSPUNKTE ***",
                ]
            )
        )
        self.assertEqual(volumes[0].mounts, ["C:\\"])
        self.assertEqual(volumes[1].mounts, [])


class ServiceTests(unittest.TestCase):
    def test_subst_without_admin_stays_in_autostart_and_gets_a_label(self) -> None:
        svc, host = service(Path("tests") / "_runtime" / "user")
        host.dirs.add(norm_path(r"C:\Projekte"))
        result = svc.apply_subst(
            SubstSpec(r"P:", r"C:\Projekte", "Projekte", r"C:\Icons\projekte.ico", True, False, True)
        )
        self.assertTrue(result.ok, result.text())
        self.assertTrue(any("Administrator" in line for line in result.warnings))
        self.assertIsNone(host.registry.get_sz("HKLM", DOS_DEVICES, "P:"))
        self.assertEqual(
            host.registry.get_sz(
                "HKCU",
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\P\DefaultLabel",
                "",
            ),
            "Projekte",
        )
        self.assertTrue(svc.autostart_enabled())
        self.assertEqual(host.subst["P"], r"C:\Projekte")
        snap = svc.snapshot()
        self.assertEqual(snap.subst[0].status, "aktiv")
        self.assertFalse(snap.subst[0].recycle)

    def test_admin_enables_dos_device_recycle_bin_and_uac(self) -> None:
        root = Path("tests") / "_runtime"
        root.mkdir(exist_ok=True)
        svc, host = service(root / "admin", admin=True)
        host.dirs.add(norm_path(r"C:\Projekte"))
        result = svc.apply_subst(SubstSpec("P", r"C:\Projekte", "Projekte", "", True, True, True, 2048))
        self.assertTrue(result.ok, result.text())
        self.assertEqual(host.registry.get_sz("HKLM", DOS_DEVICES, "P:"), r"\??\C:\Projekte")
        self.assertEqual(host.registry.get_dword("HKLM", POLICIES_SYSTEM, "EnableLinkedConnections"), 1)
        guid = svc.store.data["subst"][0]["recycle_guid"]
        relative = host.registry.get_sz("HKLM", FOLDER_DESC + "\\" + guid, "RelativePath")
        self.assertEqual(relative, "P:\\")
        self.assertEqual(host.registry.get_dword("HKCU", BITBUCKET + "\\" + guid, "NukeOnDelete"), 0)
        self.assertEqual(host.registry.get_dword("HKCU", BITBUCKET + "\\" + guid, "MaxCapacity"), 2048)
        self.assertTrue(host.task)
        removed = svc.remove_subst("P")
        self.assertTrue(removed.ok, removed.text())
        self.assertNotIn("P", host.subst)
        self.assertIsNone(host.registry.get_sz("HKLM", DOS_DEVICES, "P:"))
        self.assertIsNone(host.registry.get_sz("HKLM", FOLDER_DESC + "\\" + guid, "RelativePath"))

    def test_subst_conflict_needs_replace(self) -> None:
        root = Path("tests") / "_runtime" / "conflict"
        svc, host = service(root)
        host.dirs.add(norm_path(r"C:\Alt"))
        host.dirs.add(norm_path(r"C:\Neu"))
        self.assertTrue(svc.apply_subst(SubstSpec("P", r"C:\Alt", persistent=False)).ok)
        blocked = svc.apply_subst(SubstSpec("P", r"C:\Neu", persistent=False))
        self.assertEqual(blocked.code, "conflict")
        replaced = svc.apply_subst(SubstSpec("P", r"C:\Neu", persistent=False), replace=True)
        self.assertTrue(replaced.ok, replaced.text())
        self.assertEqual(host.subst["P"], r"C:\Neu")

    def test_net_use_does_not_store_the_password(self) -> None:
        root = Path("tests") / "_runtime" / "net"
        svc, host = service(root)
        result = svc.connect_net(NetSpec("Z", r"\\nas\archiv", "ada", "secret", True, "Archiv"))
        self.assertTrue(result.ok, result.text())
        saved = json.loads((root / "config.json").read_text(encoding="utf-8"))
        self.assertNotIn("secret", json.dumps(saved))
        self.assertEqual(saved["net"][0]["user"], "ada")
        self.assertEqual(host.registry.get_sz("HKCU", r"Network\Z", "RemotePath"), r"\\nas\archiv")
        self.assertTrue(svc.disconnect_net("Z").ok)

    def test_share_requires_admin_and_link_remove_keeps_the_target(self) -> None:
        root = Path("tests") / "_runtime" / "links"
        svc, host = service(root, admin=False)
        host.dirs.add(norm_path(r"C:\Freigabe"))
        denied = svc.create_share(ShareSpec("Projekte", r"C:\Freigabe", "READ", "ada"))
        self.assertFalse(denied.ok)
        host.set_admin(True)
        created = svc.create_share(ShareSpec("Projekte", r"C:\Freigabe", "FULL", "ada"))
        self.assertTrue(created.ok, created.text())
        self.assertIn("Projekte", host.shares)

        host.dirs.add(norm_path(r"C:\Links"))
        host.dirs.add(norm_path(r"D:\Daten"))
        missing_parent = svc.create_link(LinkSpec("junction", r"C:\Fehlt\App", r"D:\Daten"))
        self.assertFalse(missing_parent.ok)
        linked = svc.create_link(LinkSpec("junction", r"C:\Links\App", r"D:\Daten"))
        self.assertTrue(linked.ok, linked.text())
        self.assertIn("mklink", host.calls[-1][2])
        refused = svc.remove_link(r"D:\Daten")
        self.assertFalse(refused.ok)
        self.assertTrue(host.path_isdir(r"D:\Daten"))
        self.assertTrue(svc.remove_link(r"C:\Links\App").ok)
        self.assertFalse(host.is_reparse(r"C:\Links\App"))
        self.assertTrue(host.path_isdir(r"D:\Daten"))

        symlink = svc.create_link(LinkSpec("symlink_dir", r"C:\Links\Sym", r"D:\Daten"))
        self.assertTrue(symlink.ok, symlink.text())
        host.set_admin(False)
        host.registry.set_admin(False)
        blocked = svc.create_link(LinkSpec("symlink_dir", r"C:\Links\Sym2", r"D:\Daten"))
        self.assertFalse(blocked.ok)

    def test_psdrive_profile_and_mount_point(self) -> None:
        root = Path("tests") / "_runtime" / "ps"
        svc, host = service(root, admin=True)
        host.dirs.add(norm_path(r"C:\Projekte"))
        local_persist = svc.create_psdrive(PsSpec("Projekte", "FileSystem", r"C:\Projekte", True, True))
        self.assertFalse(local_persist.ok)
        created = svc.create_psdrive(PsSpec("Projekte", "FileSystem", r"C:\Projekte", True, False))
        self.assertTrue(created.ok, created.text())
        profile = host.profile_paths()[0].read_text(encoding="utf-8")
        self.assertIn("New-PSDrive -Name 'Projekte'", profile)
        self.assertIn("# --- SphereDrive BEGIN ---", profile)
        again = replace_marked_block(profile, render_profile_block([]))
        self.assertNotIn("SphereDrive BEGIN", again)
        self.assertTrue(svc.remove_psdrive("Projekte").ok)
        self.assertNotIn("New-PSDrive", host.profile_paths()[0].read_text(encoding="utf-8"))

        host.dirs.add(norm_path(r"C:\Mounts\Daten"))
        host.nonempty.add(norm_path(r"C:\Mounts\Voll"))
        host.dirs.add(norm_path(r"C:\Mounts\Voll"))
        volume = "\\\\?\\Volume{22222222-2222-2222-2222-222222222222}\\"
        blocked = svc.mount_volume(MountSpec(volume, r"C:\Mounts\Voll"))
        self.assertFalse(blocked.ok)
        mounted = svc.mount_volume(MountSpec(volume, "E"))
        self.assertTrue(mounted.ok, mounted.text())
        self.assertIn("E", host.logical_drives())
        self.assertTrue(svc.unmount_volume("E").ok)
        self.assertNotIn("E", host.logical_drives())

    def test_settings_and_restore(self) -> None:
        root = Path("tests") / "_runtime" / "settings"
        svc, host = service(root, admin=False)
        host.dirs.add(norm_path(r"C:\Projekte"))
        denied = svc.apply_settings(linked=True, autostart=True, elevated_task=False)
        self.assertFalse(denied.ok)
        host.set_admin(True)
        applied = svc.apply_settings(linked=True, autostart=True, elevated_task=True)
        self.assertTrue(applied.ok, applied.text())
        self.assertTrue(svc.linked_connections_enabled())
        self.assertTrue(svc.autostart_enabled())
        self.assertTrue(host.task)
        self.assertTrue(svc.apply_subst(SubstSpec("P", r"C:\Projekte", persistent=True)).ok)
        host.subst.clear()
        restored = svc.restore_persistent()
        self.assertTrue(all(item.ok for item in restored), [item.text() for item in restored])
        self.assertEqual(host.subst["P"], r"C:\Projekte")

    def test_drive_cards_keep_real_disks_and_virtual_mappings_apart(self) -> None:
        root = Path("tests") / "_runtime" / "cards"
        svc, host = service(root, admin=True)
        host.dirs.add(norm_path(r"C:\Projekte"))
        self.assertTrue(svc.apply_subst(SubstSpec("P", r"C:\Projekte", "Projekte", persistent=True, recycle=True)).ok)
        self.assertTrue(svc.connect_net(NetSpec("Z", r"\\nas\archiv", label="Archiv", persistent=True)).ok)
        snap = svc.snapshot()
        cards = {item.letter: item for item in svc.drive_cards(True, snap)}
        self.assertEqual(cards["C"].kind, "fixed")
        self.assertEqual(cards["C"].kind_label, "Lokaler Datenträger")
        self.assertEqual(cards["C"].title, "System (C:)")
        self.assertTrue(cards["C"].real_fixed)
        self.assertFalse(cards["C"].persistent)
        self.assertFalse(cards["C"].can_disconnect)
        self.assertTrue(cards["P"].persistent)
        self.assertEqual(cards["P"].origin, "subst")
        self.assertEqual(cards["P"].title, "Projekte (P:)")
        self.assertEqual(cards["P"].kind_label, "Virtuelles Laufwerk")
        self.assertFalse(cards["P"].real_fixed)
        self.assertTrue(cards["P"].can_disconnect)
        self.assertEqual(cards["Z"].kind_label, "Netzlaufwerk")
        self.assertEqual(cards["Z"].target, r"\\nas\archiv")
        self.assertEqual({item.letter for item in svc.drive_cards(False, snap)}, {"P", "Z"})
        occupied = svc.apply_subst(SubstSpec("C", r"C:\Projekte"))
        self.assertFalse(occupied.ok)
        self.assertEqual(occupied.code, "occupied")
        painted = svc.apply_appearance("C", "Windows", r"C:\icons\drive.ico")
        self.assertTrue(painted.ok, painted.text())
        self.assertEqual(host.registry.get_sz("HKCU", drive_icon_key("C", "DefaultLabel"), ""), "Windows")
        self.assertNotIn("C", host.subst)
        titled = {item.letter: item for item in svc.drive_cards(True)}
        self.assertEqual(titled["C"].title, "Windows (C:)")
        volume = "\\\\?\\Volume{22222222-2222-2222-2222-222222222222}\\"
        self.assertTrue(svc.mount_volume(MountSpec(volume, "E")).ok)
        mounted = {item.letter: item for item in svc.drive_cards(False)}
        self.assertIn("E", mounted)
        self.assertTrue(mounted["E"].real_fixed)
        self.assertTrue(mounted["E"].can_disconnect)
        self.assertEqual(mounted["E"].origin, "mount")

    def test_installer_restore_uses_the_bundled_launcher(self) -> None:
        root = Path("tests") / "_runtime" / "install"
        if root.exists():
            shutil.rmtree(root)
        python_dir = root / "Python"
        python_dir.mkdir(parents=True)
        (python_dir / "pythonw.exe").write_bytes(b"")
        (root / "pkgs").mkdir()
        launcher = root / "bin" / "SphereDrive.exe"
        launcher.parent.mkdir()
        launcher.write_bytes(b"")
        executable, arguments = bundled_restore(python_dir / "pythonw.exe")
        self.assertEqual(executable, str(launcher))
        self.assertEqual(arguments, "--restore")
        self.assertEqual(format_launch(executable, arguments), f'"{launcher}" --restore')
        command, args = restore_launch()
        self.assertIn("--restore", args)
        self.assertTrue(command)

    def test_icon_choice_prefers_a_custom_file(self) -> None:
        root = Path("tests") / "_runtime" / "icons"
        root.mkdir(parents=True, exist_ok=True)
        bundled = root / "SphereDrive.ico"
        custom = root / "logo.ico"
        bundled.write_bytes(b"ico")
        custom.write_bytes(b"ico")
        self.assertEqual(choose_icon([bundled, custom]), custom)
        self.assertEqual(choose_icon([bundled]), bundled)

    def test_publish_copies_program_and_keeps_a_custom_icon(self) -> None:
        source = Path("tests") / "_runtime" / "publish-src"
        target = Path("tests") / "_runtime" / "publish-dst"
        if source.exists():
            shutil.rmtree(source)
        if target.exists():
            shutil.rmtree(target)
        (source / "assets").mkdir(parents=True)
        (source / "assets" / "SphereDrive.ico").write_bytes(b"ICO")
        (source / "assets" / "SphereDrive.png").write_bytes(b"PNG")
        (source / "SphereDrive.pyw").write_text("start", encoding="utf-8")
        (source / "SphereDrive-Hilfe.html").write_text("hilfe", encoding="utf-8")
        (source / "SphereDrive-Feature-Liste.txt").write_text("liste", encoding="utf-8")
        (source / "spheredrive").mkdir()
        (source / "spheredrive" / "__init__.py").write_text("", encoding="utf-8")
        cache = source / "spheredrive" / "__pycache__"
        cache.mkdir()
        (cache / "x.pyc").write_bytes(b"0")
        copied = publish_to(target, source)
        self.assertIn("SphereDrive.pyw", copied)
        self.assertEqual((target / "SphereDrive.pyw").read_text(encoding="utf-8"), "start")
        self.assertEqual((target / "SphereDrive-Hilfe.html").read_text(encoding="utf-8"), "hilfe")
        self.assertEqual((target / "SphereDrive-Feature-Liste.txt").read_text(encoding="utf-8"), "liste")
        self.assertTrue((target / "assets" / "SphereDrive.ico").is_file())
        self.assertFalse((target / "spheredrive" / "__pycache__").exists())
        (target / "logo.ico").write_bytes(b"CUSTOM")
        place_logo(target, source)
        self.assertFalse((target / "SphereDrive.ico").exists())
        (target / "logo.ico").unlink()
        place_logo(target, source)
        self.assertEqual((target / "SphereDrive.ico").read_bytes(), b"ICO")
        self.assertIsNone(ensure_work_dir())
        self.assertEqual(system_caption(22631), "Windows 11")
        self.assertEqual(system_caption(19045), "Windows 10")
        if sys.platform != "win32":
            self.assertEqual(system_caption(), "Vorschau")

    def test_feature_list_names_the_windows_tools(self) -> None:
        self.assertIn("subst", DESCRIPTION)
        titles = [title for title, _lines in FEATURES]
        self.assertEqual(
            titles,
            [
                "Laufwerkszuordnungen",
                "Ordner und Unterordner",
                "subst",
                "net use",
                "Verknüpfungen",
                "PowerShell",
                "Bereitstellung",
                "Programm",
            ],
        )
        self.assertTrue(all(lines for _title, lines in FEATURES))
        from spheredrive.helptext import (
            FEATURE_FILE,
            HELP_FILE,
            render_feature_text,
            render_help_html,
            render_help_text,
            write_documents,
        )
        from spheredrive.paths import package_root

        html_path, feature_path = write_documents(package_root())
        help_text = render_help_text()
        feature_text = render_feature_text()
        html_text = render_help_html()
        self.assertEqual(html_path.read_text(encoding="utf-8"), html_text)
        self.assertEqual(feature_path.read_text(encoding="utf-8"), feature_text)
        self.assertEqual(html_path.name, HELP_FILE)
        self.assertEqual(feature_path.name, FEATURE_FILE)
        for title, _lines in FEATURES:
            self.assertIn(title, help_text)
            self.assertIn(title, feature_text)
            self.assertIn(title, html_text)
        self.assertIn("Freigabe verbinden", help_text)
        self.assertIn("net use X:", help_text)
        self.assertIn('<html lang="de">', html_text)
        bat = Path("Start-SphereDrive.bat").read_text(encoding="utf-8")
        installer = Path("tools/build_installer.py").read_text(encoding="utf-8")
        for name in (HELP_FILE, FEATURE_FILE):
            self.assertIn(name, bat)
            self.assertIn(name, installer)

    def test_folder_tree_includes_subfolders_and_follows_subst(self) -> None:
        svc, host = service(Path("tests") / "_runtime" / "folders")
        self.assertEqual(svc.list_folders(r"C:\Projekte"), ["Archiv", "SphereDrive"])
        self.assertEqual(svc.list_folders(r"C:\Projekte\Archiv"), ["2024", "2026"])
        self.assertEqual(svc.list_folders(r"C:\Projekte\SphereDrive"), ["assets"])
        self.assertEqual(join_path(r"C:\Projekte", "Archiv"), r"C:\Projekte\Archiv")
        host.subst["P"] = r"C:\Projekte"
        self.assertEqual(map_through_subst(r"P:\Archiv", host.subst), r"C:\Projekte\Archiv")
        self.assertEqual(svc.list_folders(r"P:\\"), ["Archiv", "SphereDrive"])
        self.assertEqual(svc.list_folders(r"P:\SphereDrive"), ["assets"])


class CliTests(unittest.TestCase):
    def test_restore_switch_exits_without_a_window(self) -> None:
        root = Path("tests") / "_runtime" / "cli"
        root.mkdir(parents=True, exist_ok=True)
        config = root / "config.json"
        previous = os.environ.get("SPHEREDRIVE_CONFIG")
        os.environ["SPHEREDRIVE_CONFIG"] = str(config)
        try:
            svc, host = service(root, admin=True)
            host.dirs.add(norm_path(r"C:\Projekte"))
            # Dieselbe Datei verwenden, die main() über die Umgebungsvariable lädt.
            svc.store.path = config
            self.assertTrue(svc.apply_subst(SubstSpec("Q", r"C:\Projekte", persistent=True)).ok)
            from spheredrive.__main__ import main

            code = main(["--restore"])
            self.assertEqual(code, 0)
        finally:
            if previous is None:
                os.environ.pop("SPHEREDRIVE_CONFIG", None)
            else:
                os.environ["SPHEREDRIVE_CONFIG"] = previous


if __name__ == "__main__":
    unittest.main()
