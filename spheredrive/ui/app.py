"""Hauptfenster."""

from __future__ import annotations

import sys
import time
import tkinter as tk
from tkinter import ttk

from spheredrive import __version__
from spheredrive.catalog import NAV_ITEMS
from spheredrive.models import OpResult, Snapshot
from spheredrive.paths import WORK_DIR, find_icon, find_window_png
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
        )
        self.work_label.pack(anchor="w", pady=(8, 0))

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
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="Aktualisieren", command=self.refresh_all, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.destroy)
        menu.add_cascade(label="Datei", menu=file_menu)
        help_menu = tk.Menu(menu, tearoff=0)
        help_menu.add_command(label="Info", command=self.show_about)
        menu.add_cascade(label="Hilfe", menu=help_menu)
        self.config(menu=menu)

    def _draw_logo(self, canvas: tk.Canvas) -> None:
        canvas.create_oval(2, 2, 34, 34, fill="#12304a", outline="")
        canvas.create_oval(7, 7, 29, 29, fill="#1d6fa8", outline="")
        canvas.create_oval(11, 9, 20, 18, fill="#d7f1ff", outline="")
        canvas.create_arc(8, 14, 28, 30, start=200, extent=140, style="arc", outline="#2bbbad", width=2)

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
        self.mode_label.configure(text="Vorschau" if snap.preview else "Windows")
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

    def show_about(self) -> None:
        icon = find_icon()
        dialog = tk.Toplevel(self)
        dialog.title("Info")
        dialog.configure(bg=P.panel)
        dialog.transient(self)
        dialog.resizable(False, False)
        text = (
            f"SphereDrive {__version__}\n\n"
            "Grafische Oberfläche für subst, net use, mklink, New-PSDrive und Bereitstellungspunkte.\n\n"
            f"Arbeitsordner: {WORK_DIR}\n"
            f"Symbol: {icon or 'keins gefunden'}\n"
            f"Konfiguration: {self.service.store.path}"
        )
        tk.Label(dialog, text=text, bg=P.panel, fg=P.text, justify="left", font=(P.font, 10), padx=18, pady=16).pack()
        Button(dialog, "Schließen", dialog.destroy, "primary").pack(pady=(0, 16))
