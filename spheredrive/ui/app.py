"""Hauptfenster."""

from __future__ import annotations

import sys
import time
import tkinter as tk
from tkinter import ttk

from spheredrive import __version__
from spheredrive.catalog import DESCRIPTION, FEATURES, NAV_ITEMS
from spheredrive.helptext import (
    FEATURE_FILE,
    HELP_FILE,
    ensure_documents,
    locate_document,
    render_feature_text,
    render_help_text,
)
from spheredrive.models import OpResult, Snapshot
from spheredrive.paths import WORK_DIR, ensure_work_dir, find_icon, find_window_png
from spheredrive.host import system_caption
from spheredrive.service import SphereService
from spheredrive.ui.pages import ComparePage, LinkPage, MountPage, NetPage, OverviewPage, PsPage, SettingsPage, SubstPage
from spheredrive.ui.widgets import Button, L, P, apply_theme, ask_yes_no, load_font


class SphereApp(tk.Tk):
    def __init__(self, service: SphereService) -> None:
        super().__init__()
        self.service = service
        self.snapshot: Snapshot | None = None
        self.current = "overview"
        self.busy = False
        load_font(self)
        apply_theme(self)
        self.title("SphereDrive")
        self.geometry("1280x840")
        self.minsize(1100, 700)
        self.configure(bg=P.bg)
        self._apply_icon()
        ensure_documents()
        self._build()
        self.bind("<F5>", lambda _event: self.refresh_all())
        self.bind_all("<Button-4>", self._wheel)
        self.bind_all("<Button-5>", self._wheel)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        if service.synchronous:
            self.refresh_all()
        else:
            self.after(30, self.refresh_all)

    def confirm(self, title: str, text: str) -> bool:
        return ask_yes_no(self, title, text)

    def _apply_icon(self) -> None:
        icon = find_icon()
        png = find_window_png()
        if icon is not None and sys.platform == "win32":
            try:
                self.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
        if png is not None:
            try:
                image = tk.PhotoImage(file=str(png))
            except tk.TclError:
                return
            self.iconphoto(True, image)
            self._icon_image = image

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.banner = tk.Label(
            self,
            text=(
                "Vorschau-Modus: Dieses System ist nicht Windows. "
                "Aktionen werden simuliert und legen keine Laufwerke an."
            ),
            bg=P.banner,
            fg=P.banner_text,
            font=(P.font, 10),
            pady=6,
        )
        if self.service.host.preview:
            self.banner.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.grid_columnconfigure(0, minsize=232)
        sidebar = tk.Frame(self, bg=P.sidebar, width=232)
        sidebar.grid(row=1, column=0, sticky="nsew")
        brand = tk.Frame(sidebar, bg=P.sidebar)
        brand.pack(fill="x", padx=16, pady=(18, 8))
        self._brand_logo = self._load_logo(36)
        if self._brand_logo is not None:
            tk.Label(brand, image=self._brand_logo, bg=P.sidebar, bd=0, highlightthickness=0).pack(side="left")
        else:
            logo = tk.Canvas(brand, width=36, height=36, bg=P.sidebar, highlightthickness=0)
            logo.pack(side="left")
            self._draw_logo(logo)
        titles = tk.Frame(brand, bg=P.sidebar)
        titles.pack(side="left", padx=(10, 0))
        tk.Label(titles, text="SphereDrive", bg=P.sidebar, fg=P.text, font=(P.font, 14, "bold")).pack(anchor="w")
        tk.Label(titles, text="Laufwerke und Links", bg=P.sidebar, fg=P.faint, font=(P.font, 9)).pack(anchor="w")

        nav = tk.Frame(sidebar, bg=P.sidebar)
        nav.pack(fill="x", pady=(12, 0))
        self.nav_buttons: dict[str, tuple[tk.Frame, tk.Button]] = {}
        for page_id, label in NAV_ITEMS:
            row = tk.Frame(nav, bg=P.sidebar)
            row.pack(fill="x")
            bar = tk.Frame(row, bg=P.sidebar, width=3)
            bar.pack(side="left", fill="y")
            button = tk.Button(
                row,
                text=label,
                command=lambda pid=page_id: self.select_page(pid),
                bg=P.sidebar,
                fg=P.muted,
                activebackground=P.card,
                activeforeground=P.text,
                relief="flat",
                bd=0,
                anchor="w",
                padx=16,
                pady=8,
                font=(P.font, 11),
                cursor="hand2",
                highlightthickness=0,
            )
            button.pack(side="left", fill="x", expand=True)
            self.nav_buttons[page_id] = (bar, button)

        footer = tk.Frame(sidebar, bg=P.sidebar)
        footer.pack(side="bottom", fill="x", padx=16, pady=16)
        self.mode_label = tk.Label(footer, text="", bg=P.sidebar, fg=P.faint, font=(P.font, 9), anchor="w")
        self.mode_label.pack(anchor="w")
        self.admin_label = tk.Label(footer, text="", bg=P.sidebar, fg=P.muted, font=(P.font, 10), anchor="w")
        self.admin_label.pack(anchor="w", pady=(2, 8))
        Button(footer, "Aktualisieren", self.refresh_all, "quiet").pack(fill="x")
        self.work_label = tk.Label(
            footer,
            text=str(WORK_DIR),
            bg=P.sidebar,
            fg=P.faint,
            font=(P.font, 8),
            anchor="w",
            wraplength=200,
            justify="left",
            cursor="hand2",
        )
        self.work_label.pack(anchor="w", pady=(8, 0))
        self.work_label.bind("<Button-1>", lambda _event: self.open_work_dir())

        content = tk.Frame(self, bg=P.bg)
        content.grid(row=1, column=1, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        self.content = content
        host = tk.Frame(content, bg=P.bg)
        self.host_frame = host
        host.grid(row=0, column=0, sticky="nsew", padx=20, pady=(16, 8))
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)

        self.pages: dict[str, ttk.Frame] = {
            "overview": OverviewPage(host, self),
            "subst": SubstPage(host, self),
            "net": NetPage(host, self),
            "links": LinkPage(host, self),
            "ps": PsPage(host, self),
            "mounts": MountPage(host, self),
            "compare": ComparePage(host, self),
            "settings": SettingsPage(host, self),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.select_page("overview")

        log_frame = tk.Frame(content, bg=P.panel, height=118)
        log_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        log_frame.grid_propagate(False)
        tk.Label(log_frame, text="Protokoll", bg=P.panel, fg=P.faint, font=(P.font, 9)).pack(anchor="w", padx=8, pady=(4, 0))
        self.log_box = tk.Text(
            log_frame,
            height=5,
            bg=P.panel,
            fg=P.muted,
            insertbackground=P.text,
            relief="flat",
            highlightthickness=0,
            font=(P.font, 9),
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.log_box.configure(state="disabled")

        status = tk.Frame(self, bg=P.sidebar, height=28)
        status.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.status_var = tk.StringVar(value="Bereit")
        tk.Label(status, textvariable=self.status_var, bg=P.sidebar, fg=P.muted, font=(P.font, 9)).pack(
            side="left", padx=12, pady=4
        )
        tk.Label(status, text=f"SphereDrive {__version__}", bg=P.sidebar, fg=P.faint, font=(P.font, 9)).pack(
            side="right", padx=12
        )

        menu = tk.Menu(self, tearoff=0)
        self.menus: dict[str, tk.Menu] = {}
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="Aktualisieren", command=self.refresh_all, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.destroy)
        menu.add_cascade(label="Datei", menu=file_menu)
        self.menus["Datei"] = file_menu
        self._tool_menu(
            menu,
            "Subst",
            [
                ("Seite öffnen", lambda: self.select_page("subst")),
                ("Ordner als Laufwerk…", self._connect_subst),
                ("Trennen…", lambda: self._disconnect_page("subst")),
            ],
        )
        self._tool_menu(
            menu,
            "net use",
            [
                ("Seite öffnen", lambda: self.select_page("net")),
                ("Freigabe verbinden…", self._connect_net),
                ("Ordner freigeben", self._open_share),
                ("Trennen…", lambda: self._disconnect_page("net")),
            ],
        )
        self._tool_menu(
            menu,
            "Verknüpfungen",
            [
                ("Seite öffnen", lambda: self.select_page("links")),
                ("Neue Verknüpfung…", lambda: self.select_page("links")),
            ],
        )
        self._tool_menu(
            menu,
            "PowerShell",
            [
                ("Seite öffnen", lambda: self.select_page("ps")),
                ("Neues Laufwerk…", lambda: self.select_page("ps")),
            ],
        )
        self._tool_menu(
            menu,
            "Bereitstellung",
            [
                ("Seite öffnen", lambda: self.select_page("mounts")),
                ("Volume bereitstellen…", lambda: self.select_page("mounts")),
                ("Datenträgerverwaltung", lambda: self.on_result(self.service.open_diskmgmt())),
            ],
        )
        self._tool_menu(
            menu,
            "Hilfe",
            [
                ("Hilfe", self.show_help),
                ("Feature-Liste", self.show_features),
                ("Hilfe-Datei öffnen", self.open_help_file),
                ("Feature-Liste öffnen", self.open_feature_file),
                None,
                ("Info", self.show_about),
            ],
        )
        self.config(menu=menu)

    def _load_logo(self, size: int) -> tk.PhotoImage | None:
        png = find_window_png()
        if png is None:
            return None
        try:
            image = tk.PhotoImage(file=str(png))
        except tk.TclError:
            return None
        step = max(image.width() // max(size, 1), 1)
        if step > 1:
            image = image.subsample(step, step)
        return image

    def _draw_logo(self, canvas: tk.Canvas) -> None:
        canvas.create_oval(2, 2, 34, 34, fill="#12304a", outline="")
        canvas.create_oval(7, 7, 29, 29, fill="#1d6fa8", outline="")
        canvas.create_oval(11, 9, 20, 18, fill="#d7f1ff", outline="")
        canvas.create_arc(8, 14, 28, 30, start=200, extent=140, style="arc", outline="#2bbbad", width=2)

    def _tool_menu(self, menu: tk.Menu, label: str, items: list[tuple[str, object] | None]) -> None:
        child = tk.Menu(menu, tearoff=0)
        for item in items:
            if item is None:
                child.add_separator()
                continue
            text, command = item
            child.add_command(label=text, command=command)
        menu.add_cascade(label=label, menu=child)
        self.menus[label] = child

    def menu_labels(self) -> list[str]:
        menu = self.nametowidget(self["menu"])
        last = menu.index("end")
        if last is None:
            return []
        labels: list[str] = []
        for index in range(last + 1):
            if menu.type(index) == "cascade":
                labels.append(str(menu.entrycget(index, "label")))
        return labels

    def _connect_subst(self) -> None:
        self.select_page("subst")
        self.pages["overview"].open_detail(None, mode="subst")

    def _connect_net(self) -> None:
        self.select_page("net")
        self.pages["overview"].open_net_use(None)

    def _open_share(self) -> None:
        self.select_page("net")
        page = self.pages["net"]
        page.update_idletasks()
        page.canvas.yview_moveto(1.0)

    def _disconnect_page(self, page_id: str) -> None:
        self.select_page(page_id)
        page = self.pages[page_id]
        if page.tree.selection():
            page.disconnect()
            return
        self.log("Zuerst ein Laufwerk in der Liste auswählen, dann Trennen.")

    def select_page(self, page_id: str) -> None:
        self.current = page_id
        canvas_bg = L.bg if page_id == "overview" else P.bg
        if hasattr(self, "content"):
            self.content.configure(bg=canvas_bg)
            self.host_frame.configure(bg=canvas_bg)
        for pid, page in self.pages.items():
            if pid == page_id:
                page.tkraise()
            bar, button = self.nav_buttons[pid]
            active = pid == page_id
            bar.configure(bg=P.accent if active else P.sidebar)
            button.configure(bg=P.card if active else P.sidebar, fg=P.text if active else P.muted)
        current = self.pages.get(page_id)
        if current is not None:
            current.after_idle(current._fit_content)

    def _wheel(self, event: tk.Event) -> None:
        page = self.pages.get(self.current)
        if page is not None:
            page.wheel(event)

    def refresh_all(self) -> None:
        def work() -> Snapshot:
            return self.service.snapshot()

        def done(result: Snapshot | OpResult) -> None:
            if isinstance(result, OpResult):
                self.log(result.text())
                return
            self.snapshot = result
            for page in self.pages.values():
                page.refresh(result)
            self._update_chrome(result)

        self.run_bg(work, done)

    def _update_chrome(self, snap: Snapshot) -> None:
        self.mode_label.configure(text="Vorschau" if snap.preview else system_caption())
        self.admin_label.configure(
            text="Administrator" if snap.admin else "Standardbenutzer",
            fg=P.teal if snap.admin else P.muted,
        )

    def run_bg(self, work, done) -> None:
        if self.busy:
            return

        def safe():
            try:
                return work()
            except Exception as exc:  # Die Oberfläche soll einen Fehler zeigen, nicht stehen bleiben.
                return OpResult(False, str(exc))

        if self.service.synchronous:
            done(safe())
            return
        self.busy = True
        self.configure(cursor="watch")
        self.status_var.set("Bitte warten …")

        def runner() -> None:
            result = safe()
            self.after(0, lambda: self._finish_bg(result, done))

        import threading

        threading.Thread(target=runner, daemon=True).start()

    def _finish_bg(self, result, done) -> None:
        self.busy = False
        self.configure(cursor="")
        done(result)

    def on_result(self, result: OpResult) -> None:
        self.log(result.text())
        page = self.pages.get(self.current)
        if page is not None and hasattr(page, "show_feedback"):
            page.show_feedback(result)
        if result.relaunch:
            self.after(200, self.destroy)
            return
        self.refresh_all()

    def log(self, text: str) -> None:
        if not text:
            return
        stamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{stamp}  {text}\n")
        end_line = int(self.log_box.index("end-1c").split(".")[0])
        if end_line > 200:
            self.log_box.delete("1.0", f"{end_line - 200}.0")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.status_var.set(text.splitlines()[0][:180])

    def open_work_dir(self) -> None:
        problem = ensure_work_dir()
        if problem:
            self.log(problem)
            return
        self.on_result(self.service.open_in_explorer(str(WORK_DIR)))

    def show_help(self) -> tk.Toplevel:
        return self._text_window("Hilfe", render_help_text())

    def show_features(self) -> tk.Toplevel:
        return self._text_window("Feature-Liste", render_feature_text())

    def open_help_file(self) -> None:
        self._open_named_document(HELP_FILE)

    def open_feature_file(self) -> None:
        self._open_named_document(FEATURE_FILE)

    def _open_named_document(self, name: str) -> None:
        ensure_documents()
        path = locate_document(name)
        if path is None:
            self.log(f"Die Datei fehlt: {name}")
            return
        self.on_result(self.service.open_in_explorer(str(path)))

    def _text_window(self, title: str, body: str) -> tk.Toplevel:
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg=P.panel)
        dialog.transient(self)
        dialog.minsize(560, 420)
        dialog.geometry("760x640")
        shell = tk.Frame(dialog, bg=P.panel)
        shell.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        scroll = ttk.Scrollbar(shell, orient="vertical")
        box = tk.Text(
            shell,
            bg=P.panel,
            fg=P.text,
            insertbackground=P.text,
            relief="flat",
            highlightthickness=0,
            font=(P.font, 11),
            wrap="word",
            yscrollcommand=scroll.set,
            padx=4,
            pady=4,
        )
        scroll.configure(command=box.yview)
        box.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        box.insert("1.0", body)
        box.configure(state="disabled")
        dialog.text = box
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        Button(dialog, "Schließen", dialog.destroy, "primary").pack(pady=(0, 16))
        return dialog

    def show_about(self) -> None:
        icon = find_icon()
        dialog = tk.Toplevel(self)
        dialog.title("Info")
        dialog.configure(bg=P.panel)
        dialog.transient(self)
        dialog.resizable(True, True)
        dialog.minsize(520, 420)
        dialog.geometry("640x720")
        dialog.logo = self._load_logo(64)
        header = tk.Frame(dialog, bg=P.panel)
        header.pack(fill="x", padx=18, pady=(16, 8))
        if dialog.logo is not None:
            tk.Label(header, image=dialog.logo, bg=P.panel, bd=0, highlightthickness=0).pack(side="left", padx=(0, 12))
        titles = tk.Frame(header, bg=P.panel)
        titles.pack(side="left", fill="x", expand=True)
        tk.Label(
            titles,
            text=f"SphereDrive {__version__}",
            bg=P.panel,
            fg=P.text,
            font=(P.font, 16, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(titles, text=system_caption(), bg=P.panel, fg=P.muted, font=(P.font, 10), anchor="w").pack(anchor="w")
        shell = tk.Frame(dialog, bg=P.panel)
        shell.pack(fill="both", expand=True, padx=18)
        canvas = tk.Canvas(shell, bg=P.panel, highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        body = tk.Frame(canvas, bg=P.panel)
        window = canvas.create_window((0, 0), window=body, anchor="nw")

        def fit(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def stretch(event: tk.Event) -> None:
            canvas.itemconfigure(window, width=event.width)

        body.bind("<Configure>", fit)
        canvas.bind("<Configure>", stretch)
        tk.Label(
            body,
            text="Beschreibung",
            bg=P.panel,
            fg=P.text,
            font=(P.font, 12, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            body,
            text=DESCRIPTION,
            bg=P.panel,
            fg=P.muted,
            font=(P.font, 10),
            justify="left",
            anchor="w",
            wraplength=560,
        ).pack(anchor="w", pady=(0, 12))
        tk.Label(body, text="Feature-Liste", bg=P.panel, fg=P.text, font=(P.font, 12, "bold"), anchor="w").pack(anchor="w")
        for title, lines in FEATURES:
            tk.Label(body, text=title, bg=P.panel, fg=P.text, font=(P.font, 11, "bold"), anchor="w").pack(
                anchor="w", pady=(10, 2)
            )
            for line in lines:
                tk.Label(
                    body,
                    text="•  " + line,
                    bg=P.panel,
                    fg=P.muted,
                    font=(P.font, 10),
                    justify="left",
                    anchor="w",
                    wraplength=560,
                ).pack(anchor="w")
        tk.Label(
            body,
            text=(
                f"Arbeitsordner: {WORK_DIR}\n"
                f"Symbol: {icon or 'keins gefunden'}\n"
                f"Konfiguration: {self.service.store.path}\n"
                f"Hilfe: {HELP_FILE}\n"
                f"Feature-Liste: {FEATURE_FILE}"
            ),
            bg=P.panel,
            fg=P.faint,
            font=(P.font, 9),
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(16, 8))
        Button(dialog, "Schließen", dialog.destroy, "primary").pack(pady=(8, 16))
