"""Dunkle Bedienelemente, die auf Windows und in der Vorschau gleich aussehen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from spheredrive.i18n import t
from spheredrive.models import OpResult


class Palette:
    bg = "#0e141b"
    sidebar = "#0b1016"
    panel = "#151c25"
    card = "#1b2531"
    line = "#2a3848"
    input = "#0c1218"
    text = "#e8eef5"
    muted = "#93a4b8"
    faint = "#6d8094"
    accent = "#3c9ee5"
    accent_dark = "#1d6fa8"
    teal = "#2bbbad"
    ok = "#3dbe7a"
    warn = "#e0a45a"
    danger = "#e15d6a"
    select = "#1a456e"
    white = "#f7fbff"
    banner = "#3a2f14"
    banner_text = "#f3d19c"
    font = "TkDefaultFont"


P = Palette()


class Light:
    """Helle Fläche für die Laufwerkskacheln, angelehnt an die Explorer-Ansicht."""

    bg = "#f5f7fa"
    paper = "#ffffff"
    line = "#e4e7ec"
    text = "#1c2430"
    muted = "#667085"
    faint = "#98a2b3"
    accent = "#1d6fa8"
    accent_soft = "#e8f3fb"
    danger = "#9f1239"
    ok = "#067647"
    hover = "#f0f6fb"


L = Light()


def load_font(root: tk.Misc) -> str:
    families = set(tkfont_families(root))
    for name in ("Segoe UI", "Liberation Sans", "DejaVu Sans", "Noto Sans"):
        if name in families:
            P.font = name
            return name
    P.font = "TkDefaultFont"
    return P.font


def tkfont_families(root: tk.Misc) -> list[str]:
    import tkinter.font as tkfont

    return list(tkfont.families(root))


def apply_theme(root: tk.Misc) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", background=P.bg, foreground=P.text, font=(P.font, 10))
    style.configure(
        "Treeview",
        background=P.input,
        fieldbackground=P.input,
        foreground=P.text,
        rowheight=28,
        borderwidth=0,
        font=(P.font, 10),
    )
    style.configure(
        "Treeview.Heading",
        background=P.card,
        foreground=P.muted,
        relief="flat",
        font=(P.font, 10),
    )
    style.map("Treeview", background=[("selected", P.select)], foreground=[("selected", P.white)])
    style.configure(
        "TCombobox",
        fieldbackground=P.input,
        background=P.card,
        foreground=P.text,
        arrowcolor=P.text,
        bordercolor=P.line,
        lightcolor=P.line,
        darkcolor=P.line,
        padding=4,
    )
    style.map("TCombobox", fieldbackground=[("readonly", P.input)], foreground=[("readonly", P.text)])
    style.configure(
        "Vertical.TScrollbar",
        background=P.card,
        troughcolor=P.bg,
        arrowcolor=P.muted,
        bordercolor=P.bg,
    )
    root.option_add("*TCombobox*Listbox.background", P.input)
    root.option_add("*TCombobox*Listbox.foreground", P.text)
    root.option_add("*TCombobox*Listbox.selectBackground", P.select)
    root.option_add("*TCombobox*Listbox.selectForeground", P.white)
    root.option_add("*TCombobox*Listbox.font", (P.font, 10))


class Button(tk.Button):
    def __init__(self, master: tk.Misc, text: str, command, kind: str = "primary") -> None:
        colors = {
            "primary": (P.accent_dark, P.white, "#2b84c7"),
            "ghost": (P.card, P.text, "#243140"),
            "danger": ("#8f2d3a", P.white, "#a83848"),
            "quiet": (P.sidebar, P.muted, P.card),
        }
        background, foreground, active = colors[kind]
        super().__init__(
            master,
            text=text,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=active,
            activeforeground=foreground,
            disabledforeground=P.faint,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=(P.font, 10),
            cursor="hand2",
            highlightthickness=0,
        )


def entry(parent: tk.Misc, variable: tk.Variable, show: str | None = None) -> tk.Entry:
    widget = tk.Entry(
        parent,
        textvariable=variable,
        bg=P.input,
        fg=P.text,
        disabledbackground=P.input,
        disabledforeground=P.faint,
        insertbackground=P.text,
        relief="flat",
        highlightthickness=1,
        highlightbackground=P.line,
        highlightcolor=P.accent,
        font=(P.font, 11),
        show=show,
    )
    return widget


def combo(parent: tk.Misc, variable: tk.Variable, values: list[str], width: int = 28) -> ttk.Combobox:
    widget = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=width, font=(P.font, 11))
    return widget


def checkbox(parent: tk.Misc, text: str, variable: tk.BooleanVar, command=None, bg: str | None = None) -> tk.Checkbutton:
    background = P.bg if bg is None else bg
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        command=command,
        bg=background,
        fg=P.text,
        activebackground=background,
        activeforeground=P.text,
        selectcolor=P.input,
        font=(P.font, 10),
        highlightthickness=0,
        anchor="w",
    )


def radio(parent: tk.Misc, text: str, variable: tk.Variable, value: str) -> tk.Radiobutton:
    return tk.Radiobutton(
        parent,
        text=text,
        variable=variable,
        value=value,
        bg=P.bg,
        fg=P.text,
        activebackground=P.bg,
        activeforeground=P.text,
        selectcolor=P.input,
        font=(P.font, 10),
        highlightthickness=0,
        bd=0,
        anchor="w",
    )


def hint(parent: tk.Misc, text: str) -> tk.Label:
    return tk.Label(
        parent,
        text=text,
        bg=P.bg,
        fg=P.faint,
        font=(P.font, 9),
        justify="left",
        anchor="w",
        wraplength=820,
    )


def caption(parent: tk.Misc, text: str) -> tk.Label:
    return tk.Label(parent, text=text, bg=P.bg, fg=P.muted, font=(P.font, 10), anchor="w")


def section(parent: tk.Misc, text: str) -> tk.Label:
    return tk.Label(parent, text=text, bg=P.bg, fg=P.text, font=(P.font, 12, "bold"), anchor="w")


def mount_tree(parent: tk.Misc, columns: list[tuple[str, str, int]], height: int = 8) -> tuple[tk.Frame, ttk.Treeview]:
    frame = tk.Frame(parent, bg=P.bg, highlightthickness=1, highlightbackground=P.line)
    ids = [item[0] for item in columns]
    tree = ttk.Treeview(frame, columns=ids, show="headings", selectmode="browse", height=height)
    for index, (cid, heading, width) in enumerate(columns):
        tree.heading(cid, text=heading, anchor="w")
        tree.column(cid, width=width, minwidth=60, anchor="w", stretch=index == len(columns) - 1)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    tree.tag_configure("good", foreground=P.ok)
    tree.tag_configure("warn", foreground=P.warn)
    tree.tag_configure("bad", foreground=P.danger)
    tree.tag_configure("muted", foreground=P.faint)
    return frame, tree


def status_tag(status: str) -> str:
    text = (status or "").lower()
    if text in {"aktiv", "ok"}:
        return "good"
    if any(word in text for word in ("fehl", "unavailable", "nicht verfügbar", "nicht verfuegbar", "disconnected")):
        return "bad"
    if any(word in text for word in ("nicht", "abweich", "sitzung")):
        return "warn"
    return "muted"


def yes_no(flag: bool) -> str:
    return t("Ja") if flag else t("Nein")


def clear_tree(tree: ttk.Treeview) -> None:
    children = tree.get_children()
    if children:
        tree.delete(*children)


def ask_yes_no(parent: tk.Misc, title: str, text: str) -> bool:
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg=P.panel)
    dialog.transient(parent)
    dialog.resizable(False, False)
    result = {"ok": False}

    tk.Label(dialog, text=title, bg=P.panel, fg=P.text, font=(P.font, 13, "bold")).pack(
        anchor="w", padx=18, pady=(16, 6)
    )
    tk.Label(
        dialog,
        text=text,
        bg=P.panel,
        fg=P.muted,
        font=(P.font, 10),
        wraplength=440,
        justify="left",
    ).pack(anchor="w", padx=18, pady=(0, 16))
    row = tk.Frame(dialog, bg=P.panel)
    row.pack(fill="x", padx=18, pady=(0, 16))

    def accept() -> None:
        result["ok"] = True
        dialog.destroy()

    def reject() -> None:
        dialog.destroy()

    Button(row, t("Nein"), reject, "ghost").pack(side="right")
    Button(row, t("Ja"), accept, "primary").pack(side="right", padx=(0, 8))
    dialog.bind("<Escape>", lambda _event: reject())
    dialog.protocol("WM_DELETE_WINDOW", reject)
    dialog.update_idletasks()
    width = max(dialog.winfo_width(), 460)
    height = dialog.winfo_height()
    x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
    y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 40)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    dialog.grab_set()
    dialog.wait_window()
    return result["ok"]


class Page(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        app: tk.Misc,
        title: str,
        subtitle: str,
        *,
        surface: str = "dark",
        show_heading: bool = True,
    ) -> None:
        self.surface = surface
        bg = P.bg if surface == "dark" else L.bg
        fg = P.text if surface == "dark" else L.text
        muted = P.muted if surface == "dark" else L.muted
        super().__init__(master, bg=bg)
        self.app = app
        self.page_bg = bg
        if show_heading:
            tk.Label(self, text=title, bg=bg, fg=fg, font=(P.font, 20, "bold")).pack(anchor="w")
            tk.Label(
                self,
                text=subtitle,
                bg=bg,
                fg=muted,
                font=(P.font, 10),
                wraplength=900,
                justify="left",
                anchor="w",
            ).pack(anchor="w", pady=(2, 8))
        shell = tk.Frame(self, bg=bg)
        shell.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(shell, bg=bg, highlightthickness=0, bd=0)
        self.vscroll = ttk.Scrollbar(shell, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._fit_content)
        self.canvas.bind("<Configure>", self._stretch_body)
        self.feedback = tk.Label(
            self,
            text="",
            bg=bg,
            fg=muted,
            font=(P.font, 10),
            wraplength=900,
            justify="left",
            anchor="w",
        )
        self.feedback.pack(fill="x", pady=(6, 0))

    def _stretch_body(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self._fit_content()

    def _fit_content(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        bbox = self.canvas.bbox("all")
        height = self.canvas.winfo_height()
        needed = bool(bbox) and height > 1 and bbox[3] > height + 2
        mapped = self.vscroll.winfo_ismapped()
        if needed and not mapped:
            self.vscroll.pack(side="right", fill="y")
        elif not needed and mapped:
            self.vscroll.pack_forget()
            self.canvas.yview_moveto(0)

    def wheel(self, event: tk.Event) -> None:
        if isinstance(event.widget, ttk.Treeview):
            return
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")

    def show_feedback(self, result: OpResult) -> None:
        self.feedback.configure(text=result.text(), fg=P.ok if result.ok else P.danger)

    def form(self) -> tk.Frame:
        frame = tk.Frame(self.body, bg=P.bg)
        frame.columnconfigure(1, weight=1)
        return frame

    def place_field(
        self,
        frame: tk.Frame,
        row: int,
        label: str,
        widget: tk.Widget,
        extra: tk.Widget | None = None,
        sticky: str = "ew",
    ) -> None:
        caption(frame, label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
        widget.grid(row=row, column=1, sticky=sticky, pady=4)
        if extra is not None:
            extra.grid(row=row, column=2, padx=(8, 0), pady=4)


def buttons(parent: tk.Misc) -> tk.Frame:
    return tk.Frame(parent, bg=P.bg)
