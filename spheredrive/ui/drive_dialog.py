"""Dialog mit allen Aktionen, die für einen Laufwerksbuchstaben zulässig sind."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from spheredrive.commands import format_bytes, suggest_letter
from spheredrive.models import DriveCard, NetSpec, OpResult, ShareSpec, SubstSpec
from spheredrive.paths import browse_directory, default_drive_icon
from spheredrive.ui.folders import FolderBrowser
from spheredrive.ui.widgets import L, P


def explorer_target(card: DriveCard) -> str:
    if card.status != "getrennt":
        return f"{card.letter}:\\"
    return card.target or f"{card.letter}:\\"


def disconnect_card(service, card: DriveCard) -> OpResult:
    if not card.can_disconnect:
        return OpResult(False, f"{card.letter}: ist ein echter Datenträger und wird nicht getrennt.")
    if card.origin == "subst":
        return service.remove_subst(card.letter)
    if card.origin == "net" or card.kind == "remote":
        return service.disconnect_net(card.letter)
    if card.origin == "mount":
        return service.unmount_volume(f"{card.letter}:")
    return OpResult(False, "Dieses Laufwerk kann nicht getrennt werden.")


class DriveDialog(tk.Toplevel):
    def __init__(self, app: tk.Misc, card: DriveCard | None, used: set[str]) -> None:
        super().__init__(app)
        self.app = app
        self.card = card
        self.used = set(used)
        self.title("Laufwerk hinzufügen" if card is None else card.title)
        self.configure(bg=L.bg)
        self.transient(app)
        self.minsize(680, 560)
        self.mode = tk.StringVar(value=self._initial_mode())
        self.letter = tk.StringVar(value=card.letter if card else suggest_letter(used))
        self.label = tk.StringVar(value="" if card is None else card.label)
        self.icon = tk.StringVar(value=_icon_file(card.icon) if card is not None else default_drive_icon())
        self.path = tk.StringVar(value=card.target if card and card.origin == "subst" else "")
        self.remote = tk.StringVar(value=card.target if card and card.origin == "net" else "")
        self.user = tk.StringVar(value="" if card is None else card.user)
        self.password = tk.StringVar()
        self.persistent = tk.BooleanVar(value=True if card is None else card.persistent)
        self.uac = tk.BooleanVar(value=False if card is None else card.uac)
        self.recycle = tk.BooleanVar(value=False if card is None else card.recycle)
        self.recycle_mb = tk.StringVar(value=str(10240 if card is None else card.recycle_mb))
        self.spawn_path = tk.StringVar(value="" if card is None else f"{card.letter}:\\")
        self.spawn_letter = tk.StringVar(value=suggest_letter(used | ({card.letter} if card else set())))
        self.spawn_persistent = tk.BooleanVar(value=True)
        self.spawn_uac = tk.BooleanVar(value=False)
        self.spawn_recycle = tk.BooleanVar(value=False)
        self.share_name = tk.StringVar()
        self._build()
        self._apply_mode()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.update_idletasks()
        width, height = 720, 680
        x = app.winfo_rootx() + max((app.winfo_width() - width) // 2, 20)
        y = app.winfo_rooty() + max((app.winfo_height() - height) // 2, 20)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _initial_mode(self) -> str:
        if self.card is None:
            return "subst"
        if self.card.real_fixed:
            return "appearance"
        if self.card.origin == "net":
            return "net"
        if self.card.origin == "subst":
            return "subst"
        return "appearance"

    def _build(self) -> None:
        footer = tk.Frame(self, bg=L.bg)
        footer.pack(side="bottom", fill="x", padx=16, pady=(4, 14))
        self._footer(footer)
        header = tk.Frame(self, bg=L.paper, highlightthickness=1, highlightbackground=L.line)
        header.pack(side="top", fill="x", padx=16, pady=(16, 8))
        self._header(header)

        shell = tk.Frame(self, bg=L.bg)
        shell.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        canvas = tk.Canvas(shell, bg=L.bg, highlightthickness=0, bd=0)
        self._canvas = canvas
        scroll = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        body = tk.Frame(canvas, bg=L.bg)
        window = canvas.create_window((0, 0), window=body, anchor="nw")

        def fit(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def stretch(event: tk.Event) -> None:
            canvas.itemconfigure(window, width=event.width)

        body.bind("<Configure>", fit)
        canvas.bind("<Configure>", stretch)
        self._form(body)
        if self.card is not None:
            self.after(30, self._reveal_folders)

    def _header(self, header: tk.Frame) -> None:
        icon = tk.Canvas(header, width=72, height=56, bg=L.paper, highlightthickness=0)
        icon.pack(side="left", padx=(12, 8), pady=12)
        kind = "subst" if self.card is None else self.card.kind
        letter = self.letter.get() or "P"
        paint_drive(icon, kind, letter)
        text = tk.Frame(header, bg=L.paper)
        text.pack(side="left", fill="x", expand=True, pady=12)
        title = "Neues virtuelles Laufwerk" if self.card is None else self.card.title
        tk.Label(text, text=title, bg=L.paper, fg=L.text, font=(P.font, 16, "bold"), anchor="w").pack(anchor="w")
        self.header_meta = tk.Label(
            text,
            text=self._meta(),
            bg=L.paper,
            fg=L.muted,
            font=(P.font, 10),
            anchor="w",
            justify="left",
        )
        self.header_meta.pack(anchor="w", pady=(2, 0))

    def _meta(self) -> str:
        if self.card is None:
            return "Subst für einen lokalen Ordner oder net use für eine Freigabe."
        parts = [self.card.kind_label]
        if self.card.status:
            parts.append(self.card.status)
        if self.card.filesystem:
            parts.append(self.card.filesystem)
        if self.card.capacity:
            parts.append(f"{format_bytes(self.card.free)} frei von {format_bytes(self.card.capacity)}")
        if self.card.target:
            parts.append(self.card.target)
        return " · ".join(parts)

    def _form(self, body: tk.Frame) -> None:
        if self.card is None:
            row = self._row(body)
            tk.Label(row, text="Buchstabe", bg=L.bg, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(side="left")
            letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            ttk.Combobox(row, textvariable=self.letter, values=letters, state="readonly", width=6).pack(side="left")

        self._labeled_entry(body, "Bezeichnung", self.label)
        icon_row = self._row(body)
        tk.Label(icon_row, text="Symbol (.ico)", bg=L.bg, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(
            side="left"
        )
        self._entry(icon_row, self.icon).pack(side="left", fill="x", expand=True)
        self._button(icon_row, "Durchsuchen", self._browse_icon, "ghost").pack(side="left", padx=(8, 0))

        box = tk.Frame(body, bg=L.paper, highlightthickness=1, highlightbackground=L.line)
        box.pack(fill="x", pady=(12, 0))
        tk.Label(box, text="Möglichkeiten", bg=L.paper, fg=L.text, font=(P.font, 12, "bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        locked = bool(self.card and self.card.real_fixed)
        self.subst_radio = self._radio(box, "Subst — lokaler Ordner als Laufwerk", "subst")
        self.net_radio = self._radio(box, "net use — Netzwerkfreigabe", "net")
        self.appearance_radio = self._radio(box, "Nur Bezeichnung und Symbol", "appearance")
        for radio in (self.subst_radio, self.net_radio, self.appearance_radio):
            radio.pack(anchor="w", padx=12, pady=1)
        if locked:
            self.subst_radio.configure(state="disabled")
            self.net_radio.configure(state="disabled")

        if self.card is None:
            tk.Label(
                box,
                text="Ordner und Unterordner eines Laufwerks",
                bg=L.paper,
                fg=L.text,
                font=(P.font, 10, "bold"),
            ).pack(anchor="w", padx=12, pady=(8, 2))
            self.folders = FolderBrowser(box, self.app, self._pick_new_folder, choose_drive=True, light=True, height=6)
            self.folders.pack(fill="x", padx=12, pady=(0, 8))
        path_row = self._row(box, L.paper)
        tk.Label(path_row, text="Ordner", bg=L.paper, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(side="left")
        self.path_entry = self._entry(path_row, self.path)
        self.path_entry.pack(side="left", fill="x", expand=True)
        self.browse_path = self._button(path_row, "Durchsuchen", self._browse_path, "ghost")
        self.browse_path.pack(side="left", padx=(8, 0))

        remote_row = self._row(box, L.paper)
        tk.Label(remote_row, text="Freigabe", bg=L.paper, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(
            side="left"
        )
        self.remote_entry = self._entry(remote_row, self.remote)
        self.remote_entry.pack(side="left", fill="x", expand=True)

        user_row = self._row(box, L.paper)
        tk.Label(user_row, text="Benutzer", bg=L.paper, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(
            side="left"
        )
        self.user_entry = self._entry(user_row, self.user)
        self.user_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(user_row, text="Kennwort", bg=L.paper, fg=L.muted, font=(P.font, 10)).pack(side="left")
        self.password_entry = self._entry(user_row, self.password, show="*")
        self.password_entry.configure(width=16)
        self.password_entry.pack(side="left", padx=(6, 0))

        checks = tk.Frame(box, bg=L.paper)
        checks.pack(anchor="w", padx=12, pady=(4, 12))
        self.persistent_box = self._check(checks, "Dauerhaft", self.persistent)
        self.persistent_box.pack(side="left", padx=(0, 12))
        self.uac_box = self._check(checks, "Für Administratoren sichtbar", self.uac)
        self.uac_box.pack(side="left", padx=(0, 12))
        self.recycle_box = self._check(checks, "Papierkorb", self.recycle, self._apply_mode)
        self.recycle_box.pack(side="left")
        tk.Label(checks, text="MB", bg=L.paper, fg=L.muted, font=(P.font, 10)).pack(side="left", padx=(8, 4))
        self.mb_entry = self._entry(checks, self.recycle_mb)
        self.mb_entry.configure(width=8)
        self.mb_entry.pack(side="left")

        self.hint = tk.Label(
            body,
            text="",
            bg=L.bg,
            fg=L.muted,
            font=(P.font, 9),
            justify="left",
            anchor="w",
            wraplength=660,
        )
        self.hint.pack(anchor="w", pady=(8, 0))

        if self.card is not None and self.card.status != "getrennt":
            self._spawn_section(body)
        if self.card is not None and self.card.origin in {"subst", "volume", "mount"} and self.card.status != "getrennt":
            self._share_section(body)

    def _spawn_section(self, body: tk.Frame) -> None:
        box = tk.Frame(body, bg=L.paper, highlightthickness=1, highlightbackground=L.line)
        box.pack(fill="x", pady=(12, 0))
        tk.Label(
            box,
            text="Ordner dieses Laufwerks als neues virtuelles Laufwerk",
            bg=L.paper,
            fg=L.text,
            font=(P.font, 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(
            box,
            text="Aufklappen zeigt die Unterordner. Ein Klick übernimmt den Ordner als neues Laufwerk.",
            bg=L.paper,
            fg=L.muted,
            font=(P.font, 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 4))
        row = self._row(box, L.paper)
        tk.Label(row, text="Ordner", bg=L.paper, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(side="left")
        self._entry(row, self.spawn_path).pack(side="left", fill="x", expand=True)
        self._button(row, "Durchsuchen", self._browse_spawn, "ghost").pack(side="left", padx=(8, 0))
        letter_row = self._row(box, L.paper)
        tk.Label(letter_row, text="Neuer Buchstabe", bg=L.paper, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(
            side="left"
        )
        free = [item for item in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if item not in self.used]
        ttk.Combobox(letter_row, textvariable=self.spawn_letter, values=free or ["Z"], state="readonly", width=6).pack(
            side="left"
        )
        self.spawn_button = self._button(letter_row, "Anlegen", self.spawn, "primary")
        self.spawn_button.pack(side="left", padx=(8, 0))
        flags = tk.Frame(box, bg=L.paper)
        flags.pack(anchor="w", padx=12, pady=(0, 6))
        self._check(flags, "Dauerhaft", self.spawn_persistent).pack(side="left", padx=(0, 12))
        self._check(flags, "Für Administratoren sichtbar", self.spawn_uac).pack(side="left", padx=(0, 12))
        self._check(flags, "Papierkorb", self.spawn_recycle).pack(side="left")
        self.folders = FolderBrowser(
            box,
            self.app,
            self._pick_spawn_folder,
            root=f"{self.card.letter}:\\",
            light=True,
            height=5,
        )
        self.folders.pack(fill="x", padx=12, pady=(0, 12))

    def _share_section(self, body: tk.Frame) -> None:
        box = tk.Frame(body, bg=L.paper, highlightthickness=1, highlightbackground=L.line)
        box.pack(fill="x", pady=(12, 0))
        tk.Label(box, text="Ordner freigeben", bg=L.paper, fg=L.text, font=(P.font, 11, "bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        row = self._row(box, L.paper)
        tk.Label(row, text="Freigabename", bg=L.paper, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(
            side="left"
        )
        self._entry(row, self.share_name).pack(side="left", fill="x", expand=True)
        self.share_button = self._button(row, "Freigabe anlegen", self.share, "ghost")
        self.share_button.pack(side="left", padx=(8, 0), pady=(0, 12))

    def _footer(self, footer: tk.Frame) -> None:
        self.save_button = self._button(footer, "Speichern", self.save, "primary")
        self.save_button.pack(side="left")
        self.explorer_button = self._button(footer, "Explorer", self.explorer, "ghost")
        self.explorer_button.pack(side="left", padx=6)
        self.disconnect_button = self._button(footer, "Trennen", self.disconnect, "danger")
        self.disconnect_button.pack(side="left", padx=(0, 6))
        if self.card is None or not self.card.can_disconnect:
            self._mute(self.disconnect_button)
        if self.card is None:
            self._mute(self.explorer_button)
        self._button(footer, "Datenträgerverwaltung", self.diskmgmt, "ghost").pack(side="left", padx=(0, 6))
        self._button(footer, "Vergleich", self.compare, "ghost").pack(side="left", padx=(0, 6))
        self._button(footer, "Schließen", self.destroy, "ghost").pack(side="right")

    def _apply_mode(self) -> None:
        mode = self.mode.get()
        subst_on = mode == "subst"
        net_on = mode == "net"
        self._enable(self.path_entry, subst_on)
        self._enable(self.browse_path, subst_on)
        self._enable(self.remote_entry, net_on)
        self._enable(self.user_entry, net_on)
        self._enable(self.password_entry, net_on)
        self._enable(self.persistent_box, mode in {"subst", "net"})
        self._enable(self.uac_box, subst_on)
        self._enable(self.recycle_box, subst_on)
        self._enable(self.mb_entry, subst_on and bool(self.recycle.get()))
        self.hint.configure(text=self._hint_text())

    def _hint_text(self) -> str:
        if self.card and self.card.real_fixed:
            return (
                f"{self.card.letter}: ist ein echter Datenträger. "
                "subst oder net use auf diesen Buchstaben würde ihn verdecken und wird deshalb nicht angeboten. "
                "Bezeichnung und Symbol können gesetzt werden. "
                "Ein Ordner auf diesem Laufwerk kann einen neuen Buchstaben bekommen. "
                "Trennen gilt nur für Subst, net use und von SphereDrive gesetzte Bereitstellungen."
            )
        mode = self.mode.get()
        if mode == "subst":
            return (
                "Subst bildet einen Ordner als Laufwerk ab. Dauerhaft schreibt den Autostart und, "
                "mit Administratorrechten, einen DOS-Devices-Eintrag. "
                "„Für Administratoren sichtbar“ setzt EnableLinkedConnections und die erhöhte Anmeldungsaufgabe. "
                "Der Papierkorb ist eine Known-Folder-Registrierung. Das Kennwort eines Netzlaufwerks wird nie gespeichert."
            )
        if mode == "net":
            return (
                "net use verbindet eine Freigabe. Dauerhaft entspricht /persistent:yes. "
                "Das Kennwort wird für den Aufruf verwendet und danach nicht gespeichert."
            )
        return "Es werden nur Bezeichnung und Symbol geschrieben. Die bestehende Zuordnung bleibt unverändert."

    def save(self) -> OpResult:
        result = self._apply()
        if result.ok:
            self.destroy()
        self.app.on_result(result)
        return result

    def _apply(self) -> OpResult:
        mode = self.mode.get()
        letter = self.letter.get()
        if self.card and self.card.real_fixed and mode in {"subst", "net"}:
            return OpResult(False, f"{self.card.letter}: ist ein echter Datenträger und wird nicht überdeckt.")
        if mode == "appearance":
            if self.card is None:
                return OpResult(False, "Ein neues Laufwerk braucht Subst oder net use.")
            return self.app.service.apply_appearance(self.card.letter, self.label.get(), self.icon.get())
        if mode == "subst":
            return self._apply_subst(letter, self.path.get(), self.persistent.get(), self.uac.get(), self.recycle.get(), self.recycle_mb.get())
        if mode == "net":
            return self._apply_net(letter)
        return OpResult(False, "Die Aktion ist unbekannt.")

    def _apply_subst(self, letter: str, path: str, persistent: bool, uac: bool, recycle: bool, capacity: str) -> OpResult:
        if self.card and self.card.origin == "net":
            if not self.app.confirm("Zuordnung ersetzen", f"{letter}: ist ein Netzlaufwerk. Zuerst trennen und als Subst neu anlegen?"):
                return OpResult(False, "Nicht geändert.")
            removed = self.app.service.disconnect_net(letter)
            if not removed.ok:
                return removed
        spec = SubstSpec(letter, path, self.label.get(), self.icon.get(), persistent, uac, recycle, _capacity(capacity))
        result = self.app.service.apply_subst(spec)
        if result.code == "conflict" and self.app.confirm("Laufwerk ersetzen", result.message + "\n\nDie bestehende Zuordnung ersetzen?"):
            result = self.app.service.apply_subst(spec, replace=True)
        return result

    def _apply_net(self, letter: str) -> OpResult:
        if self.card and self.card.origin == "subst":
            if not self.app.confirm("Zuordnung ersetzen", f"{letter}: ist ein Subst-Laufwerk. Zuerst trennen und als Netzlaufwerk verbinden?"):
                return OpResult(False, "Nicht geändert.")
            removed = self.app.service.remove_subst(letter)
            if not removed.ok:
                return removed
        password = self.password.get()
        self.password.set("")
        spec = NetSpec(
            letter,
            self.remote.get(),
            self.user.get(),
            password,
            self.persistent.get(),
            self.label.get(),
            self.icon.get(),
        )
        return self.app.service.connect_net(spec)

    def _reveal_folders(self) -> None:
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.yview_moveto(1.0)

    def _pick_new_folder(self, path: str) -> None:
        self.path.set(path)
        self.mode.set("subst")
        if not self.label.get().strip():
            self.label.set(path.rstrip("\\").split("\\")[-1])

    def _pick_spawn_folder(self, path: str) -> None:
        self.spawn_path.set(path)

    def spawn(self) -> OpResult:
        spec = SubstSpec(
            self.spawn_letter.get(),
            self.spawn_path.get(),
            "",
            "",
            self.spawn_persistent.get(),
            self.spawn_uac.get(),
            self.spawn_recycle.get(),
            10240,
        )
        result = self.app.service.apply_subst(spec)
        if result.code == "conflict" and self.app.confirm(
            "Laufwerk ersetzen", result.message + "\n\nDie bestehende Zuordnung ersetzen?"
        ):
            result = self.app.service.apply_subst(spec, replace=True)
        self.app.on_result(result)
        return result

    def share(self) -> OpResult:
        path = self.path.get().strip() if self.card and self.card.origin == "subst" else f"{self.card.letter}:\\"
        result = self.app.service.create_share(ShareSpec(self.share_name.get(), path, "READ", ""))
        self.app.on_result(result)
        return result

    def explorer(self) -> None:
        if self.card is None:
            return
        self.app.on_result(self.app.service.open_in_explorer(explorer_target(self.card)))

    def disconnect(self) -> None:
        if self.card is None or not self.card.can_disconnect:
            return
        if not self.app.confirm("Trennen", f"{self.card.letter}: wirklich trennen?"):
            return
        result = disconnect_card(self.app.service, self.card)
        if result.ok:
            self.destroy()
        self.app.on_result(result)

    def diskmgmt(self) -> None:
        self.app.on_result(self.app.service.open_diskmgmt())

    def compare(self) -> None:
        self.destroy()
        self.app.select_page("compare")

    def _browse_path(self) -> None:
        selected = filedialog.askdirectory(parent=self, title="Ordner für Subst", initialdir=browse_directory() or None)
        if selected:
            self.path.set(selected)

    def _browse_icon(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self,
            title="Laufwerkssymbol",
            initialdir=browse_directory() or None,
            filetypes=[("Symbole", "*.ico"), ("Alle Dateien", "*.*")],
        )
        if selected:
            self.icon.set(selected)

    def _browse_spawn(self) -> None:
        selected = filedialog.askdirectory(parent=self, title="Ordner auf diesem Laufwerk", initialdir=browse_directory() or None)
        if selected:
            self.spawn_path.set(selected)

    def _row(self, parent: tk.Misc, bg: str | None = None) -> tk.Frame:
        row = tk.Frame(parent, bg=bg or L.bg)
        row.pack(fill="x", pady=3, padx=12 if bg == L.paper else 0)
        return row

    def _labeled_entry(self, parent: tk.Misc, caption: str, variable: tk.StringVar) -> None:
        row = self._row(parent)
        tk.Label(row, text=caption, bg=L.bg, fg=L.muted, font=(P.font, 10), width=16, anchor="w").pack(side="left")
        self._entry(row, variable).pack(side="left", fill="x", expand=True)

    def _entry(self, parent: tk.Misc, variable: tk.StringVar, show: str | None = None) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=variable,
            bg=L.paper,
            fg=L.text,
            disabledbackground="#eef1f4",
            disabledforeground=L.faint,
            insertbackground=L.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=L.line,
            highlightcolor=L.accent,
            font=(P.font, 11),
            show=show,
        )

    def _button(self, parent: tk.Misc, text: str, command, kind: str) -> tk.Button:
        colors = {
            "primary": (L.accent, "#ffffff", "#185d90"),
            "ghost": (L.paper, L.text, L.hover),
            "danger": ("#9f1239", "#ffffff", "#881337"),
        }
        background, foreground, active = colors[kind]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=active,
            activeforeground=foreground,
            disabledforeground=L.faint,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=L.line if kind == "ghost" else background,
            padx=10,
            pady=6,
            font=(P.font, 10),
            cursor="hand2",
        )

    def _check(self, parent: tk.Misc, text: str, variable: tk.BooleanVar, command=None) -> tk.Checkbutton:
        background = parent.cget("bg")
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=command,
            bg=background,
            fg=L.text,
            activebackground=background,
            activeforeground=L.text,
            selectcolor=L.paper,
            font=(P.font, 10),
            highlightthickness=0,
            anchor="w",
        )

    def _radio(self, parent: tk.Misc, text: str, value: str) -> tk.Radiobutton:
        return tk.Radiobutton(
            parent,
            text=text,
            variable=self.mode,
            value=value,
            command=self._apply_mode,
            bg=L.paper,
            fg=L.text,
            activebackground=L.paper,
            activeforeground=L.text,
            selectcolor=L.paper,
            font=(P.font, 10),
            highlightthickness=0,
            anchor="w",
        )

    def _enable(self, widget: tk.Widget, enabled: bool) -> None:
        widget.configure(state="normal" if enabled else "disabled")

    def _mute(self, widget: tk.Button) -> None:
        widget.configure(state="disabled", bg="#e5e7eb", fg=L.faint, highlightbackground=L.line)


def _capacity(value: str) -> int:
    try:
        return int((value or "").strip() or "10240")
    except ValueError:
        return 10240


def paint_drive(canvas: tk.Canvas, kind: str, letter: str = "") -> None:
    """Kleines Laufwerkssymbol, ohne externe Bilddatei."""
    canvas.delete("all")
    if kind == "fixed" and letter.upper().startswith("C"):
        canvas.create_rectangle(14, 8, 58, 40, fill="#3c9ee5", outline="")
        canvas.create_rectangle(18, 12, 34, 24, fill="#ffffff", outline="")
        canvas.create_rectangle(36, 12, 54, 22, fill="#ffffff", outline="")
        canvas.create_rectangle(36, 24, 54, 36, fill="#ffffff", outline="")
        canvas.create_rectangle(30, 40, 42, 46, fill="#9aa3af", outline="")
        canvas.create_rectangle(22, 46, 50, 50, fill="#6b7280", outline="")
        return
    if kind == "removable":
        canvas.create_rectangle(28, 6, 46, 16, fill="#9ca3af", outline="")
        canvas.create_rectangle(24, 14, 50, 46, fill="#4b5563", outline="")
        canvas.create_rectangle(28, 22, 46, 28, fill="#e5e7eb", outline="")
        canvas.create_oval(40, 34, 46, 40, fill="#3ddc84", outline="")
        return
    if kind == "cdrom":
        canvas.create_oval(16, 8, 56, 48, fill="#d5dbe3", outline="#9aa3af")
        canvas.create_oval(30, 22, 42, 34, fill="#ffffff", outline="#9aa3af")
        return
    if kind == "remote":
        canvas.create_rectangle(8, 14, 30, 32, fill="#4b5563", outline="")
        canvas.create_rectangle(42, 14, 64, 32, fill="#4b5563", outline="")
        canvas.create_line(30, 23, 42, 23, fill="#3b82f6", width=2)
        canvas.create_rectangle(22, 36, 50, 50, fill="#374151", outline="")
        canvas.create_oval(40, 40, 46, 46, fill="#3b82f6", outline="")
        return
    canvas.create_rectangle(16, 14, 58, 40, fill="#5b6573", outline="")
    canvas.create_polygon(16, 40, 12, 50, 62, 50, 58, 40, fill="#3f4854", outline="")
    led = "#2bbbad" if kind == "subst" else "#9ca3af" if kind == "disconnected" else "#3ddc84"
    canvas.create_oval(46, 30, 54, 38, fill=led, outline="")


def _icon_file(value: str) -> str:
    text = (value or "").strip()
    if text.lower().endswith(",0"):
        return text[:-2]
    return text
