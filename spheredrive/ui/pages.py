"""Seiten für Subst, net use, mklink, New-PSDrive, Bereitstellung und Vergleich."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

from spheredrive.catalog import COMPARISON, LINK_KINDS, LINK_KIND_LABEL, PERMISSIONS, PS_PROVIDERS
from spheredrive.i18n import LANGUAGES, get_language, t
from spheredrive.commands import build_unc, normalize_letter, suggest_letter
from spheredrive.models import DriveCard, LinkSpec, MountSpec, NetSpec, OpResult, PsSpec, ShareSpec, Snapshot, SubstSpec
from spheredrive.paths import WORK_DIR, browse_directory, default_drive_icon
from spheredrive.ui.drive_dialog import DriveDialog, disconnect_card, explorer_target, paint_drive
from spheredrive.ui.folders import FolderBrowser
from spheredrive.ui.widgets import (
    Button,
    L,
    P,
    Page,
    buttons,
    checkbox,
    clear_tree,
    combo,
    entry,
    hint,
    mount_tree,
    radio,
    section,
    status_tag,
    yes_no,
)


def _initial_dir() -> str:
    folder = browse_directory()
    return folder or str(os.path.expanduser("~"))


def _used_letters(snap: Snapshot) -> set[str]:
    letters = {item.letter for item in snap.subst} | {item.letter for item in snap.net}
    for volume in snap.volumes:
        for mount in volume.mounts:
            if len(mount) >= 2 and mount[1] == ":":
                letters.add(mount[0].upper())
    return letters


class OverviewPage(Page):
    """Kachelansicht wie im Explorer: Klick öffnet alle zulässigen Aktionen des Laufwerks."""

    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("Laufwerkszuordnungen"),
            t("Kachel anklicken zeigt alle Möglichkeiten für dieses Laufwerk."),
            surface="light",
            show_heading=False,
        )
        self.cards: list[DriveCard] = []
        self.view = tk.StringVar(value="grid")
        self.show_all = tk.BooleanVar(value=True)
        self.tile_widgets: list[tk.Frame] = []
        self._by_letter: dict[str, DriveCard] = {}
        self._cols = 0
        self._dialog: DriveDialog | None = None
        self.show_all.trace_add("write", lambda *_args: self._filter_changed())
        self._build_toolbar()
        self.empty = tk.Label(
            self.body,
            text=t("Keine virtuellen Laufwerke. „Hinzufügen“ legt ein Subst- oder Netzlaufwerk an."),
            bg=L.bg,
            fg=L.muted,
            font=(P.font, 11),
            anchor="w",
        )
        self.gallery = tk.Frame(self.body, bg=L.bg)
        self.gallery.bind("<Configure>", self._on_gallery_configure)
        self._build_list()
        style = ttk.Style(self)
        style.configure(
            "Drive.Treeview",
            background=L.paper,
            fieldbackground=L.paper,
            foreground=L.text,
            rowheight=32,
            borderwidth=0,
            font=(P.font, 10),
        )
        style.configure(
            "Drive.Treeview.Heading",
            background="#eef1f5",
            foreground=L.muted,
            relief="flat",
            font=(P.font, 10),
        )
        style.map("Drive.Treeview", background=[("selected", L.accent_soft)], foreground=[("selected", L.text)])

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self.body, bg=L.bg)
        bar.pack(fill="x", pady=(0, 8))
        self._tool(bar, t("+ Hinzufügen"), self.open_add, primary=True).pack(side="left")
        self._tool(bar, t("Aktualisieren"), self.app.refresh_all).pack(side="left", padx=(8, 14))
        tk.Checkbutton(
            bar,
            text=t("Alle Laufwerke anzeigen"),
            variable=self.show_all,
            bg=L.bg,
            fg=L.text,
            activebackground=L.bg,
            activeforeground=L.text,
            selectcolor=L.paper,
            font=(P.font, 10),
            highlightthickness=0,
        ).pack(side="left")
        views = tk.Frame(bar, bg=L.bg)
        views.pack(side="right")
        self.list_button = self._tool(views, t("Liste"), lambda: self._set_view("list"))
        self.grid_button = self._tool(views, t("Kacheln"), lambda: self._set_view("grid"))
        self.grid_button.pack(side="right")
        self.list_button.pack(side="right", padx=(0, 6))
        self._mark_view()

    def _build_list(self) -> None:
        self.list_holder = tk.Frame(self.body, bg=L.paper, highlightthickness=1, highlightbackground=L.line)
        columns = ("title", "kind", "target", "status", "persistent")
        self.tree = ttk.Treeview(
            self.list_holder,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=12,
            style="Drive.Treeview",
        )
        headings = (
            ("title", t("Laufwerk"), 220),
            ("kind", t("Art"), 180),
            ("target", t("Ziel"), 320),
            ("status", t("Status"), 120),
            ("persistent", t("Dauerhaft"), 100),
        )
        for index, (cid, heading, width) in enumerate(headings):
            self.tree.heading(cid, text=heading, anchor="w")
            self.tree.column(cid, width=width, minwidth=70, anchor="w", stretch=index == 2)
        scroll = ttk.Scrollbar(self.list_holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.list_holder.rowconfigure(0, weight=1)
        self.list_holder.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._open_tree)
        self.tree.tag_configure("good", foreground=P.ok)
        self.tree.tag_configure("warn", foreground=P.warn)
        self.tree.tag_configure("bad", foreground=P.danger)
        self.tree.tag_configure("muted", foreground=L.muted)

    def _tool(self, parent: tk.Misc, text: str, command, primary: bool = False) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=L.accent if primary else L.paper,
            fg="#ffffff" if primary else L.text,
            activebackground="#185d90" if primary else L.hover,
            activeforeground="#ffffff" if primary else L.text,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=L.accent if primary else L.line,
            padx=10,
            pady=5,
            font=(P.font, 10),
            cursor="hand2",
        )

    def _mark_view(self) -> None:
        grid = self.view.get() == "grid"
        self.grid_button.configure(bg=L.accent_soft if grid else L.paper)
        self.list_button.configure(bg=L.paper if grid else L.accent_soft)

    def _set_view(self, name: str) -> None:
        self.view.set(name)
        self._mark_view()
        self._render()

    def _filter_changed(self) -> None:
        if self.app.snapshot is not None:
            self.refresh(self.app.snapshot)

    def refresh(self, snap: Snapshot) -> None:
        self.cards = list(self.app.service.drive_cards(bool(self.show_all.get()), snap))
        self._render()
        self.after_idle(self._fit_content)

    def _render(self) -> None:
        self._by_letter = {card.letter: card for card in self.cards}
        if not self.cards:
            self.gallery.pack_forget()
            self.list_holder.pack_forget()
            self.empty.pack(anchor="w", pady=28)
            return
        self.empty.pack_forget()
        if self.view.get() == "list":
            self.gallery.pack_forget()
            self._fill_list()
            self.list_holder.pack(fill="both", expand=True, pady=(4, 0))
            return
        self.list_holder.pack_forget()
        self._fill_grid()
        self.gallery.pack(fill="both", expand=True)

    def _fill_list(self) -> None:
        clear_tree(self.tree)
        for card in self.cards:
            self.tree.insert(
                "",
                "end",
                iid=card.letter,
                values=(card.title, card.kind_label, card.target, t(card.status), _durable(card)),
                tags=(status_tag(card.status),),
            )

    def _fill_grid(self) -> None:
        for child in self.gallery.winfo_children():
            child.destroy()
        self.tile_widgets = []
        self._cols = 0
        for card in self.cards:
            self.tile_widgets.append(self._tile(card))
        width = self.gallery.winfo_width()
        self._reflow(width if width > 1 else 900)

    def _tile(self, card: DriveCard) -> tk.Frame:
        tile = tk.Frame(self.gallery, bg=L.paper, width=148, height=158, highlightthickness=1, highlightbackground=L.line)
        tile.pack_propagate(False)
        menu = tk.Button(
            tile,
            text="···",
            command=lambda current=card, widget=None: None,
            bg=L.paper,
            fg=L.muted,
            activebackground=L.hover,
            activeforeground=L.text,
            relief="flat",
            bd=0,
            padx=4,
            pady=0,
            font=(P.font, 11, "bold"),
            cursor="hand2",
            highlightthickness=0,
        )
        menu.configure(command=lambda current=card, button=menu: self._popup(current, button))
        menu.place(relx=1, x=-4, y=2, anchor="ne")
        glyph = tk.Canvas(tile, width=88, height=58, bg=L.paper, highlightthickness=0)
        glyph.pack(pady=(18, 0))
        paint_drive(glyph, card.kind, card.letter)
        title = tk.Label(
            tile,
            text=_clip(card.title, 20),
            bg=L.paper,
            fg=L.text,
            font=(P.font, 10, "bold"),
        )
        title.pack()
        kind = tk.Label(tile, text=_clip(card.kind_label, 22), bg=L.paper, fg=L.muted, font=(P.font, 9))
        kind.pack()

        def open_card(_event=None, current=card) -> None:
            self.open_detail(current)

        for widget in (tile, glyph, title, kind):
            widget.bind("<Button-1>", open_card)
            widget.configure(cursor="hand2")
        tile.bind("<Enter>", lambda _event, frame=tile: frame.configure(highlightbackground=L.accent))
        tile.bind("<Leave>", lambda _event, frame=tile: frame.configure(highlightbackground=L.line))
        return tile

    def _popup(self, card: DriveCard, widget: tk.Widget) -> None:
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=L.paper,
            fg=L.text,
            activebackground=L.accent_soft,
            activeforeground=L.text,
            relief="flat",
            bd=1,
        )
        self._fill_card_menu(menu, card)
        menu.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())

    def _fill_card_menu(self, menu: tk.Menu, card: DriveCard) -> None:
        menu.add_command(label=t("Alle Möglichkeiten"), command=lambda: self.open_detail(card))
        menu.add_command(label=t("net use…"), command=lambda: self.open_net_use(card))
        menu.add_command(label=t("Im Explorer öffnen"), command=lambda: self._explorer(card))
        if card.can_disconnect:
            menu.add_command(label=t("Trennen"), command=lambda: self._disconnect(card))

    def card_menu(self, card: DriveCard) -> tk.Menu:
        menu = tk.Menu(self, tearoff=0)
        self._fill_card_menu(menu, card)
        return menu

    def _on_gallery_configure(self, event: tk.Event) -> None:
        if self.view.get() == "grid":
            self._reflow(event.width)

    def _reflow(self, width: int) -> None:
        cols = max(1, int(width) // 164)
        if cols == self._cols:
            return
        self._cols = cols
        for index, tile in enumerate(self.tile_widgets):
            tile.grid(row=index // cols, column=index % cols, padx=6, pady=6, sticky="nw")

    def _open_tree(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        card = self._by_letter.get(selected[0])
        if card is not None:
            self.open_detail(card)

    def open_add(self) -> DriveDialog:
        return self.open_detail(None)

    def open_detail(self, card: DriveCard | None, mode: str | None = None) -> DriveDialog:
        if self._dialog is not None:
            try:
                if self._dialog.winfo_exists():
                    self._dialog.destroy()
            except tk.TclError:
                pass
        used: set[str] = set()
        if self.app.snapshot is not None:
            used = {item.letter for item in self.app.service.drive_cards(True, self.app.snapshot)}
        self._dialog = DriveDialog(self.app, card, used, mode=mode)
        return self._dialog

    def open_net_use(self, card: DriveCard | None) -> DriveDialog:
        if card is not None and card.real_fixed:
            self.app.log(t("{letter}: ist ein echter Datenträger. net use verwendet einen freien Buchstaben.", letter=card.letter))
            return self.open_detail(None, mode="net")
        return self.open_detail(card, mode="net")

    def _explorer(self, card: DriveCard) -> None:
        self.app.on_result(self.app.service.open_in_explorer(explorer_target(card)))

    def _disconnect(self, card: DriveCard) -> None:
        if not self.app.confirm(t("Trennen"), t("{letter}: wirklich trennen?", letter=card.letter)):
            return
        self.app.on_result(disconnect_card(self.app.service, card))


def _durable(card: DriveCard) -> str:
    if card.origin == "volume":
        return "—"
    return yes_no(card.persistent)


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


class SubstPage(Page):
    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("Subst"),
            t(
                "Lokale Ordner — auch OneDrive, Google Drive oder Dropbox — als eigenes Laufwerk. "
                "Bezeichnung, Symbol und Papierkorb setzt Windows mit subst allein nicht."
            ),
        )
        self.letter = tk.StringVar()
        self.path = tk.StringVar()
        self.label = tk.StringVar()
        self.icon = tk.StringVar(value=default_drive_icon())
        self.persistent = tk.BooleanVar(value=True)
        self.uac = tk.BooleanVar(value=False)
        self.recycle = tk.BooleanVar(value=False)
        self.recycle_mb = tk.StringVar(value="10240")
        self.letter_touched = False
        form = self.form()
        form.pack(fill="x")
        self.place_field(
            form, 0, t("Laufwerk"), combo(form, self.letter, list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), 6), sticky="w"
        )
        self.letter.trace_add("write", self._touch_letter)
        self.place_field(form, 1, t("Ordner"), entry(form, self.path), Button(form, t("Durchsuchen"), self.browse_path, "ghost"))
        self.place_field(form, 2, t("Bezeichnung"), entry(form, self.label))
        self.place_field(form, 3, t("Symbol (.ico)"), entry(form, self.icon), Button(form, t("Durchsuchen"), self.browse_icon, "ghost"))
        checks = tk.Frame(form, bg=P.bg)
        checks.grid(row=4, column=1, columnspan=2, sticky="w", pady=(2, 0))
        checkbox(checks, t("Dauerhaft"), self.persistent).pack(side="left", padx=(0, 14))
        checkbox(checks, t("Für Administratoren sichtbar"), self.uac).pack(side="left", padx=(0, 14))
        checkbox(checks, t("Papierkorb"), self.recycle, self._toggle_mb).pack(side="left")
        caption = tk.Label(checks, text=t("MB"), bg=P.bg, fg=P.muted, font=(P.font, 10))
        caption.pack(side="left", padx=(10, 4))
        self.mb_entry = entry(checks, self.recycle_mb)
        self.mb_entry.configure(width=8)
        self.mb_entry.pack(side="left")
        self._toggle_mb()
        hint(
            self.body,
            t(
                "Dauerhaft schreibt den Autostart und, mit Administratorrechten, ein DOS-Device. "
                "Das DOS-Device gilt nach dem Neustart auch für Programme, die als Administrator laufen. "
                "Zusätzlich setzt „Für Administratoren sichtbar“ EnableLinkedConnections und eine erhöhte Anmeldungsaufgabe. "
                "Der Papierkorb ist eine Known-Folder-Registrierung und braucht ebenfalls Administratorrechte."
            ),
        ).pack(anchor="w", pady=(6, 4))
        tk.Label(self.body, text=t("Ordner und Unterordner"), bg=P.bg, fg=P.text, font=(P.font, 11, "bold")).pack(anchor="w")
        self.folders = FolderBrowser(self.body, self.app, self._pick_folder, choose_drive=True, height=6)
        self.folders.pack(fill="x", pady=(2, 8))
        row = buttons(self.body)
        row.pack(anchor="w", pady=(0, 8))
        Button(row, t("Verbinden"), self.connect, "primary").pack(side="left")
        Button(row, t("Trennen"), self.disconnect, "danger").pack(side="left", padx=8)
        Button(row, t("Explorer"), self.open_selected, "ghost").pack(side="left")
        holder, self.tree = mount_tree(
            self.body,
            [
                ("letter", t("Laufwerk"), 90),
                ("path", t("Ordner"), 280),
                ("label", t("Bezeichnung"), 140),
                ("status", t("Status"), 130),
                ("persistent", t("Dauerhaft"), 90),
                ("uac", t("UAC"), 70),
                ("recycle", t("Papierkorb"), 90),
            ],
        )
        holder.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda _event: self.open_selected())
        self._rows = {}

    def _touch_letter(self, *_args) -> None:
        if self.letter.get():
            self.letter_touched = True

    def _toggle_mb(self) -> None:
        self.mb_entry.configure(state="normal" if self.recycle.get() else "disabled")

    def refresh(self, snap: Snapshot) -> None:
        if not self.letter_touched:
            self.letter.set(suggest_letter(_used_letters(snap)))
        clear_tree(self.tree)
        self._rows = {}
        for item in snap.subst:
            self._rows[item.letter] = item
            self.tree.insert(
                "",
                "end",
                iid=item.letter,
                values=(
                    f"{item.letter}:",
                    item.path,
                    item.label,
                    t(item.status),
                    yes_no(item.persistent),
                    yes_no(item.uac),
                    yes_no(item.recycle),
                ),
                tags=(status_tag(item.status),),
            )

    def on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected or selected[0] not in self._rows:
            return
        item = self._rows[selected[0]]
        self.letter_touched = True
        self.letter.set(item.letter)
        self.path.set(item.path)
        self.label.set(item.label)
        self.icon.set(item.icon.split(",")[0] if item.icon else "")
        self.persistent.set(item.persistent)
        self.uac.set(item.uac)
        self.recycle.set(item.recycle)
        self.recycle_mb.set(str(item.recycle_mb))
        self._toggle_mb()

    def spec(self) -> SubstSpec:
        try:
            capacity = int(self.recycle_mb.get().strip() or "10240")
        except ValueError:
            capacity = 10240
        return SubstSpec(
            self.letter.get(),
            self.path.get(),
            self.label.get(),
            self.icon.get(),
            self.persistent.get(),
            self.uac.get(),
            self.recycle.get(),
            capacity,
        )

    def connect(self) -> None:
        spec = self.spec()

        def done(result: OpResult) -> None:
            if result.code == "conflict" and self.app.confirm(
                t("Laufwerk ersetzen"),
                t(
                    "{letter}: ist schon verbunden. Durch den neuen Ordner ersetzen?",
                    letter=normalize_letter(spec.letter) or spec.letter,
                ),
            ):
                self.app.run_bg(lambda: self.app.service.apply_subst(spec, replace=True), self.app.on_result)
                return
            self.app.on_result(result)

        self.app.run_bg(lambda: self.app.service.apply_subst(spec, replace=False), done)

    def disconnect(self) -> None:
        letter = self.letter.get()
        if not normalize_letter(letter):
            self.show_feedback(OpResult(False, t("Kein Laufwerk ausgewählt.")))
            return
        if not self.app.confirm(
            t("Laufwerk trennen"),
            t("{letter}: trennen? Bezeichnung, Symbol und Papierkorb-Registrierung werden mit entfernt.", letter=letter),
        ):
            return
        self.app.run_bg(lambda: self.app.service.remove_subst(letter), self.app.on_result)

    def open_selected(self) -> None:
        letter = normalize_letter(self.letter.get())
        if letter is None:
            return
        self.app.on_result(self.app.service.open_in_explorer(f"{letter}:\\"))

    def _pick_folder(self, path: str) -> None:
        self.path.set(path)
        folder_name = path.rstrip("\\").split("\\")[-1]
        if folder_name and not self.label.get().strip():
            self.label.set(folder_name)

    def browse_path(self) -> None:
        chosen = filedialog.askdirectory(parent=self.app, initialdir=_initial_dir())
        if chosen:
            self.path.set(chosen)

    def browse_icon(self) -> None:
        chosen = filedialog.askopenfilename(
            parent=self.app,
            initialdir=_initial_dir(),
            filetypes=[(t("Symbole"), "*.ico"), (t("Alle Dateien"), "*.*")],
        )
        if chosen:
            self.icon.set(chosen)


class NetPage(Page):
    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("Netzlaufwerke"),
            t(
                "net use verbindet eine Freigabe als Laufwerk. Mit „Dauerhaft“ bleibt sie über /persistent:yes erhalten. "
                "Ein lokaler Ordner geht denselben Weg, sobald er freigegeben ist."
            ),
        )
        self.letter = tk.StringVar()
        self.mode = tk.StringVar(value="unc")
        self.remote = tk.StringVar()
        self.computer = tk.StringVar(value=os.environ.get("COMPUTERNAME") or "localhost")
        self.share = tk.StringVar()
        self.user = tk.StringVar()
        self.password = tk.StringVar()
        self.persistent = tk.BooleanVar(value=True)
        self.label = tk.StringVar()
        self.icon = tk.StringVar(value=default_drive_icon())
        self.share_name = tk.StringVar()
        self.share_path = tk.StringVar()
        self.permission = tk.StringVar(value=t("Lesen"))
        self.principal = tk.StringVar(value=os.environ.get("USERNAME") or os.environ.get("USER") or "")
        self.letter_touched = False
        form = self.form()
        form.pack(fill="x")
        self.place_field(
            form, 0, t("Laufwerk"), combo(form, self.letter, list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), 6), sticky="w"
        )
        self.letter.trace_add("write", lambda *_args: setattr(self, "letter_touched", True))
        mode = tk.Frame(form, bg=P.bg)
        radio(mode, t("UNC-Freigabe"), self.mode, "unc").pack(side="left")
        radio(mode, t("Vorhandene Freigabe eines Computers"), self.mode, "local").pack(side="left", padx=(12, 0))
        self.place_field(form, 1, t("Art"), mode)
        self.place_field(form, 2, "UNC", entry(form, self.remote))
        host = tk.Frame(form, bg=P.bg)
        entry(host, self.computer).pack(side="left", fill="x", expand=True)
        tk.Label(host, text=t("Freigabe"), bg=P.bg, fg=P.muted, font=(P.font, 10)).pack(side="left", padx=8)
        entry(host, self.share).pack(side="left", fill="x", expand=True)
        self.place_field(form, 3, t("Computer"), host)
        self.place_field(form, 4, t("Benutzer"), entry(form, self.user))
        self.place_field(form, 5, t("Kennwort"), entry(form, self.password, show="*"))
        self.place_field(form, 6, t("Bezeichnung"), entry(form, self.label))
        checks = tk.Frame(form, bg=P.bg)
        checks.grid(row=7, column=1, sticky="w")
        checkbox(checks, t("Dauerhaft (/persistent:yes)"), self.persistent).pack(side="left")
        hint(
            self.body,
            t(
                "Das Kennwort wird nicht gespeichert. Bei leerem Kennwort und gesetztem Benutzer verwendet Windows /savecred. "
                "Administrative Freigaben wie \\\\localhost\\C$\\Ordner brauchen Administratorrechte."
            ),
        ).pack(anchor="w", pady=(4, 4))
        row = buttons(self.body)
        row.pack(anchor="w", pady=(0, 6))
        Button(row, t("Verbinden"), self.connect, "primary").pack(side="left")
        Button(row, t("Trennen"), self.disconnect, "danger").pack(side="left", padx=8)
        Button(row, t("Explorer"), self.open_selected, "ghost").pack(side="left")
        holder, self.tree = mount_tree(
            self.body,
            [
                ("letter", t("Laufwerk"), 90),
                ("remote", t("Freigabe"), 320),
                ("status", t("Status"), 140),
                ("persistent", t("Dauerhaft"), 90),
                ("label", t("Bezeichnung"), 160),
            ],
            height=4,
        )
        holder.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        section(self.body, t("Ordner freigeben")).pack(anchor="w", pady=(10, 4))
        share_form = self.form()
        share_form.pack(fill="x")
        self.place_field(share_form, 0, t("Name"), entry(share_form, self.share_name))
        self.place_field(
            share_form, 1, t("Ordner"), entry(share_form, self.share_path), Button(share_form, t("Durchsuchen"), self.browse_share, "ghost")
        )
        perm_row = tk.Frame(share_form, bg=P.bg)
        combo(perm_row, self.permission, [t(label) for _key, label in PERMISSIONS], 16).pack(side="left")
        tk.Label(perm_row, text=t("Konto"), bg=P.bg, fg=P.muted, font=(P.font, 10)).pack(side="left", padx=8)
        entry(perm_row, self.principal).pack(side="left", fill="x", expand=True)
        self.place_field(share_form, 2, t("Rechte"), perm_row)
        share_buttons = buttons(self.body)
        share_buttons.pack(anchor="w", pady=(4, 4))
        Button(share_buttons, t("Freigabe erstellen"), self.create_share, "primary").pack(side="left")
        Button(share_buttons, t("Freigabe entfernen"), self.delete_share, "danger").pack(side="left", padx=8)
        Button(share_buttons, t("Freigabeverwaltung"), self.open_manager, "ghost").pack(side="left")
        holder2, self.shares = mount_tree(
            self.body,
            [("name", t("Freigabe"), 160), ("path", "Pfad", 360), ("remark", "Bemerkung", 220)],
            height=4,
        )
        holder2.pack(fill="both", expand=True, pady=(4, 0))
        self.shares.bind("<<TreeviewSelect>>", self.on_share_select)
        self._rows = {}

    def refresh(self, snap: Snapshot) -> None:
        if not self.letter_touched:
            self.letter.set(suggest_letter(_used_letters(snap)))
        clear_tree(self.tree)
        clear_tree(self.shares)
        self._rows = {item.letter: item for item in snap.net}
        for item in snap.net:
            self.tree.insert(
                "",
                "end",
                iid=item.letter,
                values=(f"{item.letter}:", item.remote, t(item.status), yes_no(item.persistent), item.label),
                tags=(status_tag(item.status),),
            )
        for index, item in enumerate(snap.shares):
            self.shares.insert("", "end", iid=f"share-{index}", values=(item.name, item.path, item.remark))

    def on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected or selected[0] not in self._rows:
            return
        item = self._rows[selected[0]]
        self.letter_touched = True
        self.letter.set(item.letter)
        self.mode.set("unc")
        self.remote.set(item.remote)
        self.user.set(item.user)
        self.persistent.set(item.persistent)
        self.label.set(item.label)
        self.icon.set(item.icon)

    def on_share_select(self, _event=None) -> None:
        selected = self.shares.selection()
        if not selected:
            return
        values = self.shares.item(selected[0], "values")
        if values:
            self.share_name.set(values[0])
            self.share_path.set(values[1])

    def _remote(self) -> str:
        if self.mode.get() == "local":
            return build_unc(self.computer.get(), self.share.get()) or ""
        return self.remote.get().strip()

    def connect(self) -> None:
        remote = self._remote()
        if not remote:
            self.show_feedback(OpResult(False, t("Die Freigabe ist unvollständig.")))
            return
        spec = NetSpec(
            self.letter.get(),
            remote,
            self.user.get(),
            self.password.get(),
            self.persistent.get(),
            self.label.get(),
            self.icon.get(),
        )
        self.password.set("")
        self.app.run_bg(lambda: self.app.service.connect_net(spec), self.app.on_result)

    def disconnect(self) -> None:
        letter = self.letter.get()
        if not self.app.confirm(t("Trennen"), t("Netzlaufwerk {letter}: trennen?", letter=letter)):
            return
        self.app.run_bg(lambda: self.app.service.disconnect_net(letter), self.app.on_result)

    def open_selected(self) -> None:
        letter = normalize_letter(self.letter.get())
        if letter:
            self.app.on_result(self.app.service.open_in_explorer(f"{letter}:\\"))

    def create_share(self) -> None:
        if not self.app.confirm(
            t("Freigabe erstellen"),
            t("Der Ordner wird im Netzwerk erreichbar. Die Dateien bleiben an ihrem Ort. Fortfahren?"),
        ):
            return
        permission = "READ"
        for key, label in PERMISSIONS:
            if label == self.permission.get() or t(label) == self.permission.get():
                permission = key
        spec = ShareSpec(self.share_name.get(), self.share_path.get(), permission, self.principal.get())
        self.app.run_bg(lambda: self.app.service.create_share(spec), self.app.on_result)

    def delete_share(self) -> None:
        name = self.share_name.get().strip()
        if not name:
            self.show_feedback(OpResult(False, t("Keine Freigabe ausgewählt.")))
            return
        if not self.app.confirm(t("Freigabe entfernen"), t("Freigabe {name} entfernen? Dateien werden nicht gelöscht.", name=name)):
            return
        self.app.run_bg(lambda: self.app.service.delete_share(name), self.app.on_result)

    def open_manager(self) -> None:
        self.app.run_bg(self.app.service.open_share_manager, self.app.on_result)

    def browse_share(self) -> None:
        chosen = filedialog.askdirectory(parent=self.app, initialdir=_initial_dir())
        if chosen:
            self.share_path.set(chosen)


class LinkPage(Page):
    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("Verknüpfungen"),
            t(
                "mklink legt den Verweis im NTFS-Dateisystem ab. Eine Junction braucht keine Administratorrechte "
                "und übersteht Neustarts ohne Autostart."
            ),
        )
        self.kind = tk.StringVar(value=t(LINK_KINDS[0][1]))
        self.link = tk.StringVar()
        self.target = tk.StringVar()
        self.scan_folder = tk.StringVar()
        form = self.form()
        form.pack(fill="x")
        self.place_field(form, 0, t("Art"), combo(form, self.kind, [t(label) for _key, label in LINK_KINDS], 42))
        self.place_field(form, 1, t("Link-Pfad"), entry(form, self.link), Button(form, t("Durchsuchen"), self.browse_link, "ghost"))
        self.place_field(form, 2, t("Ziel"), entry(form, self.target), Button(form, t("Durchsuchen"), self.browse_target, "ghost"))
        hint(
            self.body,
            t(
                "Entfernen löscht nur die Verknüpfung, nicht das Ziel. Symbolische Links brauchen Administratorrechte "
                "oder den Entwicklermodus. Harte Links sind weitere Namen derselben Datei."
            ),
        ).pack(anchor="w", pady=(6, 4))
        row = buttons(self.body)
        row.pack(anchor="w", pady=(0, 8))
        Button(row, t("Erstellen"), self.create, "primary").pack(side="left")
        Button(row, t("Nur Link entfernen"), self.remove, "danger").pack(side="left", padx=8)
        Button(row, t("Ziel öffnen"), self.open_target, "ghost").pack(side="left")
        holder, self.tree = mount_tree(
            self.body,
            [
                ("kind", t("Art"), 260),
                ("link", t("Link"), 280),
                ("target", t("Ziel"), 280),
                ("status", t("Status"), 100),
            ],
        )
        holder.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        scan = tk.Frame(self.body, bg=P.bg)
        scan.pack(fill="x", pady=(8, 0))
        scan.columnconfigure(1, weight=1)
        tk.Label(scan, text=t("Ordner durchsuchen"), bg=P.bg, fg=P.muted, font=(P.font, 10)).grid(row=0, column=0, padx=(0, 12))
        entry(scan, self.scan_folder).grid(row=0, column=1, sticky="ew")
        Button(scan, t("Durchsuchen"), self.browse_scan, "ghost").grid(row=0, column=2, padx=8)
        Button(scan, t("Links übernehmen"), self.scan, "primary").grid(row=0, column=3)
        self._rows = {}

    def _kind_key(self) -> str:
        label = self.kind.get()
        for key, text in LINK_KINDS:
            if text == label or t(text) == label:
                return key
        return "junction"

    def refresh(self, snap: Snapshot) -> None:
        clear_tree(self.tree)
        self._rows = {}
        for index, item in enumerate(snap.links):
            iid = f"link-{index}"
            self._rows[iid] = item
            from spheredrive.catalog import LINK_KIND_LABEL

            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(t(LINK_KIND_LABEL.get(item.kind, item.kind)), item.link, item.target, t(item.status)),
                tags=(status_tag(item.status),),
            )

    def on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected or selected[0] not in self._rows:
            return
        item = self._rows[selected[0]]
        from spheredrive.catalog import LINK_KIND_LABEL

        self.kind.set(t(LINK_KIND_LABEL.get(item.kind, LINK_KINDS[0][1])))
        self.link.set(item.link)
        self.target.set(item.target)

    def create(self) -> None:
        spec = LinkSpec(self._kind_key(), self.link.get(), self.target.get())
        self.app.run_bg(lambda: self.app.service.create_link(spec), self.app.on_result)

    def remove(self) -> None:
        path = self.link.get().strip()
        if not path:
            self.show_feedback(OpResult(False, t("Kein Link ausgewählt.")))
            return
        text = t("Nur die Verknüpfung entfernen? Das Ziel bleibt erhalten.")
        if self._kind_key() == "hardlink":
            text = (
                "Diesen Hardlink-Namen entfernen? Die Datei bleibt erhalten, solange mindestens ein weiterer Name existiert. "
                "Ist es der letzte Name, löscht Windows die Datei."
            )
        if not self.app.confirm(t("Verknüpfung entfernen"), text):
            return
        self.app.run_bg(lambda: self.app.service.remove_link(path), self.app.on_result)

    def open_target(self) -> None:
        target = self.target.get().strip() or self.link.get().strip()
        if target:
            self.app.on_result(self.app.service.open_in_explorer(target))

    def scan(self) -> None:
        folder = self.scan_folder.get().strip()
        self.app.run_bg(lambda: self.app.service.scan_links(folder), self.app.on_result)

    def browse_link(self) -> None:
        chosen = filedialog.askdirectory(parent=self.app, initialdir=_initial_dir())
        if chosen:
            self.link.set(chosen)

    def browse_target(self) -> None:
        if self._kind_key() in {"junction", "symlink_dir"}:
            chosen = filedialog.askdirectory(parent=self.app, initialdir=_initial_dir())
        else:
            chosen = filedialog.askopenfilename(parent=self.app, initialdir=_initial_dir())
        if chosen:
            self.target.set(chosen)

    def browse_scan(self) -> None:
        chosen = filedialog.askdirectory(parent=self.app, initialdir=_initial_dir())
        if chosen:
            self.scan_folder.set(chosen)


class PsPage(Page):
    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("PowerShell"),
            t(
                "New-PSDrive kann Ordner, die Registrierung und Zertifikatspeicher als Laufwerk anlegen. "
                "Ohne Profil existiert es nur in der PowerShell-Sitzung."
            ),
        )
        self.name = tk.StringVar()
        self.provider = tk.StringVar(value="FileSystem")
        self.root = tk.StringVar()
        self.profile = tk.BooleanVar(value=False)
        self.persist = tk.BooleanVar(value=False)
        form = self.form()
        form.pack(fill="x")
        self.place_field(form, 0, t("Name"), entry(form, self.name))
        self.place_field(form, 1, t("Anbieter"), combo(form, self.provider, [item[0] for item in PS_PROVIDERS], 24))
        self.provider.trace_add("write", lambda *_args: self._show_hint())
        self.place_field(form, 2, t("Stamm"), entry(form, self.root), Button(form, t("Durchsuchen"), self.browse_root, "ghost"))
        checks = tk.Frame(form, bg=P.bg)
        checks.grid(row=3, column=1, sticky="w")
        checkbox(checks, t("In jedes neue PowerShell-Fenster (Profil)"), self.profile).pack(side="left", padx=(0, 12))
        checkbox(checks, t("-Persist (nur UNC)"), self.persist).pack(side="left")
        self.provider_hint = hint(self.body, "")
        self.provider_hint.pack(anchor="w", pady=(6, 4))
        self._show_hint()
        row = buttons(self.body)
        row.pack(anchor="w", pady=(0, 8))
        Button(row, t("Anlegen"), self.create, "primary").pack(side="left")
        Button(row, t("Entfernen"), self.remove, "danger").pack(side="left", padx=8)
        Button(row, t("PowerShell öffnen"), self.open_console, "ghost").pack(side="left")
        Button(row, t("Stamm öffnen"), self.open_root, "ghost").pack(side="left", padx=8)
        holder, self.tree = mount_tree(
            self.body,
            [
                ("name", t("Name"), 140),
                ("provider", t("Anbieter"), 140),
                ("root", t("Stamm"), 320),
                ("profile", t("Profil"), 80),
                ("status", t("Status"), 120),
            ],
        )
        holder.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self._rows = {}

    def _show_hint(self) -> None:
        for name, _label, text in PS_PROVIDERS:
            if name == self.provider.get():
                self.provider_hint.configure(text=t(text))
                return

    def refresh(self, snap: Snapshot) -> None:
        clear_tree(self.tree)
        self._rows = {}
        for item in snap.psdrives:
            self._rows[item.name] = item
            self.tree.insert(
                "",
                "end",
                iid=item.name,
                values=(item.name, item.provider, item.root, yes_no(item.profile), t(item.status)),
                tags=(status_tag(item.status),),
            )

    def on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected or selected[0] not in self._rows:
            return
        item = self._rows[selected[0]]
        self.name.set(item.name)
        self.provider.set(item.provider)
        self.root.set(item.root)
        self.profile.set(item.profile)
        self.persist.set(item.persist_windows)

    def _spec(self) -> PsSpec:
        return PsSpec(self.name.get(), self.provider.get(), self.root.get(), self.profile.get(), self.persist.get())

    def create(self) -> None:
        spec = self._spec()
        self.app.run_bg(lambda: self.app.service.create_psdrive(spec), self.app.on_result)

    def remove(self) -> None:
        name = self.name.get().strip()
        if not name:
            self.show_feedback(OpResult(False, t("Kein PowerShell-Laufwerk ausgewählt.")))
            return
        if not self.app.confirm(t("Entfernen"), t("PowerShell-Laufwerk {name} entfernen?", name=name)):
            return
        self.app.run_bg(lambda: self.app.service.remove_psdrive(name), self.app.on_result)

    def open_console(self) -> None:
        spec = self._spec()
        self.app.run_bg(lambda: self.app.service.open_powershell(spec), self.app.on_result)

    def open_root(self) -> None:
        root = self.root.get().strip()
        if root:
            self.app.on_result(self.app.service.open_in_explorer(root))

    def browse_root(self) -> None:
        if self.provider.get() != "FileSystem":
            return
        chosen = filedialog.askdirectory(parent=self.app, initialdir=_initial_dir())
        if chosen:
            self.root.set(chosen)


class MountPage(Page):
    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("Bereitstellung"),
            t(
                "Partitionen und virtuelle Festplatten (VHD/VHDX) lassen sich auf einen Buchstaben oder in einen leeren "
                "NTFS-Ordner legen. Das bleibt über den Volume-Manager erhalten."
            ),
        )
        self.volume = tk.StringVar()
        self.mode = tk.StringVar(value="folder")
        self.letter = tk.StringVar(value="E")
        self.folder = tk.StringVar()
        form = self.form()
        form.pack(fill="x")
        self.place_field(form, 0, t("Volume"), entry(form, self.volume))
        mode = tk.Frame(form, bg=P.bg)
        radio(mode, t("Laufwerksbuchstabe"), self.mode, "letter").pack(side="left")
        combo(mode, self.letter, list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), 4).pack(side="left", padx=(8, 16))
        radio(mode, t("Leerer NTFS-Ordner"), self.mode, "folder").pack(side="left")
        self.place_field(form, 1, t("Ziel"), mode)
        self.place_field(form, 2, t("Ordner"), entry(form, self.folder), Button(form, t("Durchsuchen"), self.browse, "ghost"))
        hint(
            self.body,
            t(
                "Der Ordner muss leer sein. Eine VHD legst du in der Datenträgerverwaltung an "
                "(Aktion, Virtuelle Festplatte erstellen) und stellst sie danach hier oder dort in einen Ordner bereit. "
                "Aufheben entfernt nur den Bereitstellungspunkt, nicht das Volume. "
                "Im Baum darunter kann ein Unterordner des Laufwerks das Ziel sein."
            ),
        ).pack(anchor="w", pady=(6, 4))
        tk.Label(self.body, text=t("Ordner und Unterordner"), bg=P.bg, fg=P.text, font=(P.font, 11, "bold")).pack(anchor="w")
        self.folders = FolderBrowser(self.body, self.app, self._pick_mount_folder, choose_drive=True, height=6)
        self.folders.pack(fill="x", pady=(2, 8))
        row = buttons(self.body)
        row.pack(anchor="w", pady=(0, 8))
        Button(row, t("Bereitstellen"), self.mount, "primary").pack(side="left")
        Button(row, t("Bereitstellung aufheben"), self.unmount, "danger").pack(side="left", padx=8)
        Button(row, t("Datenträgerverwaltung"), self.diskmgmt, "ghost").pack(side="left")
        holder, self.tree = mount_tree(
            self.body,
            [
                ("id", t("Volume"), 280),
                ("label", t("Bezeichnung"), 120),
                ("fs", t("Dateisystem"), 90),
                ("size", t("Größe"), 90),
                ("free", t("Frei"), 90),
                ("mounts", t("Bereitstellung"), 220),
            ],
        )
        holder.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def refresh(self, snap: Snapshot) -> None:
        from spheredrive.commands import format_bytes

        clear_tree(self.tree)
        for index, item in enumerate(snap.volumes):
            self.tree.insert(
                "",
                "end",
                iid=f"vol-{index}",
                values=(
                    item.id,
                    item.label,
                    item.filesystem,
                    format_bytes(item.capacity) if item.capacity else "",
                    format_bytes(item.free) if item.free else "",
                    ", ".join(item.mounts) if item.mounts else t("nicht bereitgestellt"),
                ),
            )

    def on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        if values:
            self.volume.set(values[0])
            mounts = values[5]
            if mounts and mounts != t("nicht bereitgestellt"):
                first = mounts.split(",")[0].strip()
                if len(first) >= 2 and first[1] == ":":
                    self.mode.set("letter")
                    self.letter.set(first[0])
                else:
                    self.mode.set("folder")
                    self.folder.set(first)

    def _target(self) -> str:
        if self.mode.get() == "letter":
            return self.letter.get()
        return self.folder.get()

    def mount(self) -> None:
        target = self._target().strip()
        volume = self.volume.get().strip()
        if not volume or not target:
            self.show_feedback(OpResult(False, t("Volume und Ziel werden beide benötigt.")))
            return
        if not self.app.confirm(t("Volume bereitstellen"), t("{volume}\nunter {target} bereitstellen?", volume=volume, target=target)):
            return
        spec = MountSpec(volume, target)
        self.app.run_bg(lambda: self.app.service.mount_volume(spec), self.app.on_result)

    def unmount(self) -> None:
        target = self._target().strip()
        if not target:
            self.show_feedback(OpResult(False, t("Kein Bereitstellungsziel ausgewählt.")))
            return
        if not self.app.confirm(t("Bereitstellung aufheben"), t("{target} trennen? Das Volume bleibt erhalten.", target=target)):
            return
        self.app.run_bg(lambda: self.app.service.unmount_volume(target), self.app.on_result)

    def diskmgmt(self) -> None:
        self.app.run_bg(self.app.service.open_diskmgmt, self.app.on_result)

    def _pick_mount_folder(self, path: str) -> None:
        self.folder.set(path)
        self.mode.set("folder")

    def browse(self) -> None:
        chosen = filedialog.askdirectory(parent=self.app, initialdir=_initial_dir())
        if chosen:
            self.folder.set(chosen)
            self.mode.set("folder")


class ComparePage(Page):
    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("Vergleich"),
            t("Welcher Befehl wohin gehört. SphereDrive spricht sie an, ändert aber ihre Eigenschaften nicht."),
        )
        holder, self.tree = mount_tree(
            self.body,
            [
                ("befehl", t("Befehl"), 170),
                ("ziel", t("Ziel-Typ"), 180),
                ("erstellt", t("Erstellt"), 230),
                ("neustart", t("Übersteht Neustart?"), 170),
                ("sphere", "SphereDrive", 280),
            ],
            height=8,
        )
        holder.pack(fill="both", expand=True)
        for index, row in enumerate(COMPARISON):
            self.tree.insert(
                "",
                "end",
                iid=f"cmp-{index}",
                values=(row["befehl"], t(row["ziel"]), t(row["erstellt"]), t(row["neustart"]), t(row["spheredrive"])),
            )
        tk.Label(
            self.body,
            text=t(
                "Subst-Laufwerke sind nach einem Neustart weg, löschen Dateien sofort und bleiben Programmen "
                "mit Administratorrechten verborgen. Dagegen helfen Autostart, DOS Devices, EnableLinkedConnections "
                "und die Known-Folder-Registrierung für den Papierkorb. net use ist der Weg über das Netzwerk. "
                "Junctions bleiben ohne Laufwerksbuchstaben im Dateisystem. New-PSDrive bleibt eine PowerShell-Sicht. "
                "Echte Partitionen und VHDs gehören in die Bereitstellung."
            ),
            bg=P.bg,
            fg=P.muted,
            justify="left",
            anchor="w",
            wraplength=900,
            font=(P.font, 10),
        ).pack(anchor="w", pady=(12, 0))

    def refresh(self, snap: Snapshot) -> None:
        del snap


class SettingsPage(Page):
    def __init__(self, master: tk.Misc, app: tk.Misc) -> None:
        super().__init__(
            master,
            app,
            t("Einstellungen"),
            t(
                "Diese Schalter gelten für alle Zuordnungen. Administratorrechte sind für die Maschinenrichtlinie, "
                "den Papierkorb und die erhöhte Anmeldungsaufgabe nötig."
            ),
        )
        self.linked = tk.BooleanVar()
        self.autostart = tk.BooleanVar(value=True)
        self.task = tk.BooleanVar()
        self.config_path = tk.StringVar()
        box = tk.Frame(self.body, bg=P.card, highlightthickness=1, highlightbackground=P.line)
        box.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(box, bg=P.card)
        inner.pack(fill="x", padx=14, pady=12)
        lang_row = tk.Frame(inner, bg=P.card)
        lang_row.pack(fill="x", pady=(0, 10))
        tk.Label(lang_row, text=t("Sprache"), bg=P.card, fg=P.text, font=(P.font, 11, "bold")).pack(side="left")
        self.language_name = tk.StringVar(value=dict(LANGUAGES).get(get_language(), "Deutsch"))
        picker = ttk.Combobox(
            lang_row,
            textvariable=self.language_name,
            values=[name for _code, name in LANGUAGES],
            state="readonly",
            width=18,
        )
        picker.pack(side="left", padx=(12, 0))
        picker.bind("<<ComboboxSelected>>", self._choose_language)
        checkbox(inner, t("EnableLinkedConnections (Laufwerke in erhöhten Programmen sichtbar)"), self.linked, bg=P.card).pack(anchor="w")
        tk.Label(
            inner,
            text=t("Registrierungswert unter Policies\\System. Wirkt nach einem Neustart. Behebt die Lücke von subst und net use."),
            bg=P.card,
            fg=P.faint,
            font=(P.font, 9),
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        checkbox(inner, t("SphereDrive bei der Anmeldung starten und Zuordnungen wiederherstellen"), self.autostart, bg=P.card).pack(anchor="w")
        tk.Label(
            inner,
            text=t("Schreibt HKCU\\...\\Run. Der Start erfolgt ohne Fenster über SphereDrive.pyw --restore."),
            bg=P.card,
            fg=P.faint,
            font=(P.font, 9),
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        checkbox(inner, t("Anmeldungsaufgabe mit höchsten Rechten"), self.task, bg=P.card).pack(anchor="w")
        tk.Label(
            inner,
            text=t("Die Aufgabe wird einmal angelegt und ruft danach ohne erneute Rückfrage --restore auf, damit auch die erhöhte Sitzung die Laufwerke sieht."),
            bg=P.card,
            fg=P.faint,
            font=(P.font, 9),
            wraplength=820,
            justify="left",
        ).pack(anchor="w")
        row = buttons(self.body)
        row.pack(anchor="w", pady=(0, 8))
        Button(row, t("Einstellungen speichern"), self.apply, "primary").pack(side="left")
        Button(row, t("Jetzt wiederherstellen"), self.restore, "ghost").pack(side="left", padx=8)
        Button(row, t("Explorer-Ansicht aktualisieren"), self.refresh_shell, "ghost").pack(side="left")
        row2 = buttons(self.body)
        row2.pack(anchor="w", pady=(0, 8))
        Button(row2, t("Als Administrator neu starten"), self.elevate, "primary").pack(side="left")
        Button(row2, t("Explorer neu starten"), self.restart_explorer, "danger").pack(side="left", padx=8)
        Button(row2, t("Konfigurationsordner"), self.open_config, "ghost").pack(side="left")
        tk.Label(self.body, textvariable=self.config_path, bg=P.bg, fg=P.faint, font=(P.font, 9), anchor="w").pack(anchor="w")

    def _choose_language(self, _event=None) -> None:
        name = self.language_name.get()
        for code, label in LANGUAGES:
            if label == name:
                self.app.apply_language(code)
                return

    def refresh(self, snap: Snapshot) -> None:
        self.linked.set(snap.linked_connections)
        self.autostart.set(snap.autostart)
        self.task.set(snap.elevated_task)
        self.config_path.set(str(self.app.service.store.path))

    def apply(self) -> None:
        linked = self.linked.get()
        autostart = self.autostart.get()
        task = self.task.get()
        self.app.run_bg(
            lambda: self.app.service.apply_settings(linked=linked, autostart=autostart, elevated_task=task),
            self.app.on_result,
        )

    def restore(self) -> None:
        def work() -> OpResult:
            results = self.app.service.restore_persistent()
            failed = [item for item in results if not item.ok]
            text = "\n".join(item.text() for item in results)
            return OpResult(not failed, text or t("Nichts wiederherzustellen."))

        self.app.run_bg(work, self.app.on_result)

    def refresh_shell(self) -> None:
        self.app.run_bg(self.app.service.refresh_shell, self.app.on_result)

    def restart_explorer(self) -> None:
        if not self.app.confirm(t("Explorer neu starten"), t("Alle Explorer-Fenster werden geschlossen und neu geöffnet.")):
            return
        self.app.run_bg(self.app.service.restart_explorer, self.app.on_result)

    def elevate(self) -> None:
        self.app.run_bg(self.app.service.elevate, self.app.on_result)

    def open_config(self) -> None:
        self.app.run_bg(self.app.service.open_config_dir, self.app.on_result)
