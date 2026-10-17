"""Klickt die Oberfläche im Vorschau-Modus durch, ohne eine Windows-Laufwerkszuordnung zu ändern."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from spheredrive.catalog import NAV_ITEMS
from spheredrive.host import PreviewHost
from spheredrive.service import SphereService


def _display_available() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


@unittest.skipUnless(_display_available(), "kein Grafikdisplay")
class GuiTests(unittest.TestCase):
    def test_pages_and_actions(self) -> None:
        import tkinter as tk

        from spheredrive.ui.app import SphereApp

        root = Path(tempfile.mkdtemp(prefix="spheredrive-gui-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        host = PreviewHost(root=root / "home")
        host.strict_paths = False
        host.set_admin(True)
        app = SphereApp(SphereService(host=host, store_path=root / "config.json"))
        app.confirm = lambda *_args, **_kwargs: True
        self.addCleanup(app.destroy)
        app.update_idletasks()
        self.assertEqual(set(app.pages), {item[0] for item in NAV_ITEMS})
        self.assertIn("Vorschau", app.banner.cget("text"))

        for page_id in app.pages:
            app.select_page(page_id)
            app.update_idletasks()
            self.assertEqual(app.current, page_id)

        subst = app.pages["subst"]
        self.assertTrue(subst.icon.get().lower().endswith("spheredrive.ico"))
        self.assertIsNotNone(app._brand_logo)
        subst.path.set(r"C:\Projekte\SphereDrive")
        subst.label.set("Projekte")
        subst.persistent.set(True)
        subst.recycle.set(True)
        subst.uac.set(True)
        subst.connect()
        app.update_idletasks()
        self.assertIn("P", host.subst)
        self.assertEqual(len(subst.tree.get_children()), 1)

        net = app.pages["net"]
        app.select_page("net")
        net.letter_touched = True
        net.letter.set("Z")
        net.mode.set("unc")
        net.remote.set(r"\\nas\archiv")
        net.user.set("ada")
        net.password.set("secret")
        net.label.set("Archiv")
        net.connect()
        saved = json.loads((root / "config.json").read_text(encoding="utf-8"))
        self.assertNotIn("secret", json.dumps(saved))
        self.assertEqual(net.password.get(), "")
        self.assertIn("Z", host.net)

        net.share_name.set("Projekte")
        net.share_path.set(r"C:\Projekte\SphereDrive")
        net.permission.set("Lesen")
        net.create_share()
        self.assertIn("Projekte", host.shares)

        links = app.pages["links"]
        app.select_page("links")
        links.kind.set("Verzeichnis-Junction (mklink /J)")
        links.link.set(r"C:\Links\Projekte")
        links.target.set(r"D:\Daten\Projekte")
        links.create()
        self.assertTrue(host.is_reparse(r"C:\Links\Projekte"))
        links.remove()
        self.assertFalse(host.is_reparse(r"C:\Links\Projekte"))

        ps = app.pages["ps"]
        app.select_page("ps")
        ps.name.set("Projekte")
        ps.provider.set("FileSystem")
        ps.root.set(r"C:\Projekte\SphereDrive")
        ps.profile.set(True)
        ps.create()
        profile = host.profile_paths()[0].read_text(encoding="utf-8")
        self.assertIn("New-PSDrive -Name 'Projekte'", profile)

        mounts = app.pages["mounts"]
        app.select_page("mounts")
        volume_id = ""
        for item in mounts.tree.get_children():
            values = mounts.tree.item(item, "values")
            if "nicht bereitgestellt" in values[5]:
                volume_id = values[0]
        self.assertTrue(volume_id)
        mounts.volume.set(volume_id)
        mounts.mode.set("letter")
        mounts.letter.set("E")
        mounts.mount()
        self.assertIn("E", host.logical_drives())
        mounts.unmount()
        self.assertNotIn("E", host.logical_drives())

        settings = app.pages["settings"]
        app.select_page("settings")
        settings.linked.set(True)
        settings.autostart.set(True)
        settings.task.set(True)
        settings.apply()
        self.assertEqual(
            host.registry.get_dword(
                "HKLM",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                "EnableLinkedConnections",
            ),
            1,
        )
        self.assertTrue(host.task)
        app.select_page("overview")
        app.update_idletasks()
        overview = app.pages["overview"]
        letters = {card.letter for card in overview.cards}
        self.assertIn("C", letters)
        self.assertIn("P", letters)
        self.assertIn("Z", letters)
        self.assertTrue(overview.show_all.get())
        virtual = next(card for card in overview.cards if card.letter == "P")
        dialog = overview.open_detail(virtual)
        app.update_idletasks()
        self.assertEqual(dialog.mode.get(), "subst")
        self.assertEqual(dialog.subst_radio.cget("state"), "normal")
        self.assertEqual(dialog.net_radio.cget("state"), "normal")
        self.assertIn("Dauerhaft", dialog.persistent_box.cget("text"))
        self.assertIn("Administratoren", dialog.uac_box.cget("text"))
        self.assertIn("Papierkorb", dialog.recycle_box.cget("text"))
        self.assertEqual(dialog.path.get(), r"C:\Projekte\SphereDrive")
        self.assertTrue(dialog.icon.get().lower().endswith("spheredrive.ico"))
        fixed = overview.open_detail(next(card for card in overview.cards if card.letter == "C"))
        app.update_idletasks()
        self.assertEqual(fixed.mode.get(), "appearance")
        self.assertEqual(fixed.subst_radio.cget("state"), "disabled")
        self.assertEqual(fixed.net_radio.cget("state"), "disabled")
        self.assertEqual(fixed.disconnect_button.cget("state"), "disabled")
        self.assertIn("echter Datenträger", fixed.hint.cget("text"))
        self.assertEqual(fixed.icon.get(), "")
        self.assertTrue(hasattr(fixed, "spawn_button"))
        fixed.label.set("Windows")
        fixed.icon.set(r"C:\icons\drive.ico")
        saved = fixed.save()
        self.assertTrue(saved.ok, saved.text())
        self.assertNotIn("C", host.subst)
        overview.show_all.set(False)
        app.update_idletasks()
        hidden = {card.letter for card in overview.cards}
        self.assertNotIn("C", hidden)
        self.assertIn("P", hidden)
        self.assertIn("Z", hidden)
        overview.show_all.set(True)
        added = overview.open_add()
        self.assertTrue(added.icon.get().lower().endswith("spheredrive.ico"))
        added.letter.set("R")
        added.path.set(r"C:\Temp\Neu")
        added.label.set("Neu")
        created = added.save()
        self.assertTrue(created.ok, created.text())
        self.assertEqual(host.subst["R"], r"C:\Temp\Neu")
        overview._set_view("list")
        app.update_idletasks()
        self.assertIn("P", overview.tree.get_children())
        overview._set_view("grid")
        # Das Fenster muss gemappt sein, sonst bleibt ein späterer Screenshot leer.
        app.deiconify()
        app.update()


if __name__ == "__main__":
    unittest.main()
