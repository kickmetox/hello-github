"""Baum der Ordner und Unterordner eines Laufwerks."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from spheredrive.commands import _windows_parts, join_path
from spheredrive.ui.widgets import L, P


class FolderBrowser(tk.Frame):
    """Zeigt die Ordner eines Laufwerks und lädt Unterordner beim Aufklappen."""

    def __init__(
        self,
        master: tk.Misc,
        app: tk.Misc,
        on_pick: Callable[[str], None],
        *,
        root: str = "",
        choose_drive: bool = False,
        light: bool = False,
        height: int = 7,
    ) -> None:
        bg = L.paper if light else P.bg
        super().__init__(master, bg=bg)
        self.app = app
        self.on_pick = on_pick
        self._loaded: set[str] = set()
        self.root_path = tk.StringVar(value=root)
        if choose_drive:
            bar = tk.Frame(self, bg=bg)
            bar.pack(fill="x", pady=(0, 4))
            tk.Label(bar, text="Laufwerk", bg=bg, fg=L.muted if light else P.muted, font=(P.font, 10)).pack(side="left")
            letters = [f"{item}:\\" for item in self.app.service.drive_letters()] or ["C:\\"]
            if not self.root_path.get():
                preferred = "C:\\" if "C:\\" in letters else letters[0]
                self.root_path.set(preferred)
            ttk.Combobox(bar, textvariable=self.root_path, values=letters, state="readonly", width=6).pack(
                side="left", padx=(8, 0)
            )
            self.root_path.trace_add("write", lambda *_args: self.reload())
        style_name = "FolderLight.Treeview" if light else "Treeview"
        if light:
            style = ttk.Style(self)
            style.configure(
                style_name,
                background=L.paper,
                fieldbackground=L.paper,
                foreground=L.text,
                rowheight=24,
                borderwidth=0,
                font=(P.font, 10),
            )
            style.map(style_name, background=[("selected", L.accent_soft)], foreground=[("selected", L.text)])
        self.tree = ttk.Treeview(self, show="tree", height=height, style=style_name)
        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.reload()

    def reload(self) -> None:
        self._loaded.clear()
        self.tree.delete(*self.tree.get_children(""))
        root = self.root_path.get().strip()
        if root:
            self._add_level("", root)

    def reveal(self, path: str) -> None:
        """Klappt den Pfad bis zum genannten Ordner auf."""
        _kind, parts = _windows_parts(path)
        if len(parts) < 2:
            return
        current = parts[0] + "\\"
        for name in parts[1:]:
            self._load(current)
            current = join_path(current, name)
            if not self.tree.exists(current):
                return
        self._load(current)

    def choose(self, path: str) -> None:
        self.reveal(path)
        if not self.tree.exists(path):
            return
        self.tree.selection_set(path)
        self.tree.focus(path)
        self.tree.see(path)
        self.on_pick(path)

    def _on_open(self, _event=None) -> None:
        item = self.tree.focus()
        if item:
            self._load(item)

    def _on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected or str(selected[0]).endswith("|~"):
            return
        self.on_pick(str(selected[0]))

    def _load(self, path: str) -> None:
        if not path or path in self._loaded or not self.tree.exists(path):
            return
        self._loaded.add(path)
        for child in self.tree.get_children(path):
            self.tree.delete(child)
        self._add_level(path, path)

    def _add_level(self, parent: str, directory: str) -> None:
        for name in self.app.service.list_folders(directory):
            full = join_path(directory, name)
            if self.tree.exists(full):
                continue
            self.tree.insert(parent, "end", iid=full, text=name)
            self.tree.insert(full, "end", iid=full + "|~", text="")
