"""Shared Tkinter widgets and helpers."""

import sqlite3
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Callable, Optional

from active_records import ValidationError
from ui import theme
from ui.icons import button_icon, icon
from ui.theme import px

_BUTTON_STYLES = {
    "primary": ("Primary.TButton", theme.WHITE),
    "danger": ("Danger.TButton", theme.DANGER),
    "quiet": ("Quiet.TButton", theme.MUTED),
    "secondary": ("TButton", theme.TEXT),
}


def show_error(parent, exc):
    if isinstance(exc, ValidationError):
        messagebox.showerror("Invalid operation", str(exc), parent=parent)
    elif isinstance(exc, sqlite3.IntegrityError):
        messagebox.showerror("Database rule", f"The operation violates a database rule:\n{exc}", parent=parent)
    else:
        messagebox.showerror("Error", f"Unexpected error:\n{exc}", parent=parent)


def run_action(parent, action):
    """Run action(); show known errors. Returns True on success."""
    try:
        action()
        return True
    except (ValidationError, sqlite3.Error) as exc:
        show_error(parent, exc)
        return False


def confirm(parent, message):
    return messagebox.askyesno("Confirm", message, parent=parent)


def short(text, length=60):
    if not text:
        return ""
    text = " ".join(str(text).split())
    return text if len(text) <= length else text[: length - 1] + "…"


def format_datetime(iso):
    return iso[:16].replace("T", " ") if iso else ""


def make_button(parent, text, command, icon_name=None, kind="secondary", **options):
    style, color = _BUTTON_STYLES[kind]
    if icon_name:
        options.update(image=button_icon(icon_name, 14 if kind == "quiet" else 16, color), compound="left")
    return ttk.Button(parent, text=f" {text}" if icon_name else text, command=command, style=style, **options)


def make_text(parent, height=4, width=50):
    """Multi-line input matching the ttk entries; Tab moves the focus instead of inserting a tab."""
    widget = tk.Text(parent, width=width, height=height, wrap="word", font=theme.FONT, relief="flat",
                     background=theme.SURFACE, foreground=theme.TEXT, insertbackground=theme.TEXT,
                     highlightthickness=1, highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
                     padx=px(6), pady=px(5))

    def move_focus(target):
        target.focus_set()
        return "break"

    widget.bind("<Tab>", lambda e: move_focus(widget.tk_focusNext()))
    widget.bind("<Shift-Tab>", lambda e: move_focus(widget.tk_focusPrev()))
    return widget


@dataclass
class Action:
    """A toolbar button of a ListPanel."""

    text: str
    command: Callable
    icon: Optional[str] = None
    kind: str = "secondary"
    needs_selection: bool = True
    key: Optional[str] = None  # used with ListPanel.set_enabled() / button()


class ThinBar(tk.Frame):
    """Slim progress bar (clam's ttk.Progressbar can't be made this thin). set() takes a fraction from 0 to 1."""

    def __init__(self, parent, color=theme.ACCENT, thickness=6, width=None):
        super().__init__(parent, background=theme.BORDER, height=px(thickness), width=px(width) if width else 0)
        self.fill = tk.Frame(self, background=color)
        self.set(0)

    def set(self, fraction):
        self.fill.place(x=0, y=0, relheight=1, relwidth=max(0.0, min(1.0, fraction)))


def _sort_key(value):
    text = "" if value is None else str(value)
    try:
        return (0, float(text), "")
    except ValueError:
        return (1, 0.0, text.casefold())


class ListPanel(ttk.Frame):
    """Card with a title, a toolbar, a sortable list and an empty state. Row iids are record ids.

    columns: (heading, width) or (heading, width, stretch).
    A row is (id, values) or (id, values, (icon_name, icon_color)); status_column adds a narrow icon column.
    """

    def __init__(self, parent, title, columns, actions, on_select=None, on_activate=None, on_delete=None,
                 searchable=False, status_column=False, auto_select=False):
        super().__init__(parent, style="Card.TFrame", padding=px(14))
        self._on_select = on_select
        self._on_activate = on_activate
        self._on_delete = on_delete
        self._auto_select = auto_select
        self._title = title
        self._rows = []
        self._sort_column = None
        self._sort_reverse = False
        self._disabled_keys = set()
        self._empty = ("information", "Nothing here yet", "", None)
        self._rendered_empty = None
        self._empty_hint = None
        self._search = tk.StringVar()

        self._build_header(title)
        self._build_toolbar(actions, searchable)
        self._build_tree(columns, status_column)
        self._sync_actions()

    # --- construction ---

    def _build_header(self, title):
        header = ttk.Frame(self, style="Surface.TFrame")
        header.pack(fill="x")
        self.title_label = ttk.Label(header, text=title, style="Section.TLabel")
        self.title_label.pack(side="left")
        self.count_label = ttk.Label(header, style="SurfaceMuted.TLabel")
        self.count_label.pack(side="left", padx=(px(8), 0))
        self.subtitle_label = ttk.Label(self, style="SurfaceMuted.TLabel", justify="left")
        self.bind("<Configure>", lambda e: self.subtitle_label.configure(wraplength=max(px(120), e.width - px(30))))

    def _build_toolbar(self, actions, searchable):
        self.toolbar = ttk.Frame(self, style="Surface.TFrame")
        self.toolbar.pack(fill="x", pady=(px(10), px(10)))
        self._actions = actions
        self._buttons = {}
        for action in actions:
            button = make_button(self.toolbar, action.text, action.command, action.icon, action.kind)
            button.pack(side="left", padx=(0, px(6)))
            self._buttons[action.key or action.text] = button
        if searchable:
            entry = ttk.Entry(self.toolbar, textvariable=self._search, width=24)
            entry.pack(side="right")
            entry.bind("<Escape>", lambda e: self._search.set(""))
            ttk.Label(self.toolbar, image=icon("zoom", 16, theme.MUTED), style="Surface.TLabel").pack(
                side="right", padx=(px(12), px(6)))
            self._search.trace_add("write", lambda *a: self._render())

    def _build_tree(self, columns, status_column):
        tk.Frame(self, background=theme.BORDER, height=1).pack(fill="x")
        self.tree_frame = ttk.Frame(self, style="Surface.TFrame")
        self.tree_frame.pack(fill="both", expand=True)
        names = [f"c{i}" for i in range(len(columns))]
        self.tree = ttk.Treeview(self.tree_frame, columns=names, selectmode="browse",
                                 show="tree headings" if status_column else "headings")
        if status_column:
            self.tree.column("#0", width=px(34), minwidth=px(34), stretch=False, anchor="center")
        self._headings = {}
        self._fixed_width = px(34) if status_column else 0
        self._stretch_widths = {}
        for name, column in zip(names, columns):
            heading, width = column[0], column[1]
            stretch = column[2] if len(column) > 2 else True
            self._headings[name] = heading
            if stretch:
                self._stretch_widths[name] = px(width)
            else:
                self._fixed_width += px(width)
            self.tree.heading(name, text=heading, anchor="w", command=lambda n=name: self._toggle_sort(n))
            self.tree.column(name, width=px(width), minwidth=px(40), anchor="w", stretch=stretch)
        self.scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self._on_tree_scrolled)
        self.tree.pack(side="left", fill="both", expand=True)
        self.empty_frame = ttk.Frame(self.tree, style="Surface.TFrame")

        self.tree.bind("<Configure>", self._on_tree_resized)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._selection_changed())
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", lambda e: self._activate())
        self.tree.bind("<Delete>", lambda e: self._delete())

    def _on_tree_scrolled(self, first, last):
        """Show the scrollbar only while the rows don't fit."""
        self.scroll.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.scroll.pack_forget()
        elif not self.scroll.winfo_manager():
            self.scroll.pack(side="right", fill="y")

    def _on_tree_resized(self, event):
        """Keep all columns visible: stretchable ones share the width the fixed ones leave free."""
        total = sum(self._stretch_widths.values())
        free = event.width - self._fixed_width - px(2)
        for name, width in self._stretch_widths.items():
            self.tree.column(name, width=max(px(40), free * width // total))
        self._fit_empty_hint()

    def _fit_empty_hint(self):
        if self._empty_hint is not None:
            self._empty_hint.configure(wraplength=max(px(120), min(px(260), self.tree.winfo_width() - px(24))))

    # --- public API ---

    def set_rows(self, rows):
        """Keeps the selection when the id is still present."""
        self._rows = [(row[0], row[1], row[2] if len(row) > 2 else None) for row in rows]
        self._render()

    def selected_id(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def select(self, row_id):
        if row_id and self.tree.exists(row_id):
            self.tree.selection_set(row_id)
            self.tree.see(row_id)
            self.tree.focus(row_id)

    def set_subtitle(self, text):
        """Short context line under the title; hidden when empty."""
        self.subtitle_label.configure(text=text or "")
        if text:
            self.subtitle_label.pack(after=self.title_label.master, anchor="w", fill="x", pady=(px(2), 0))
        else:
            self.subtitle_label.pack_forget()

    def set_empty(self, icon_name, title, hint="", action=None):
        """What to show when the list has no rows. action: optional (text, command, icon)."""
        self._empty = (icon_name, title, hint, action)
        self._render_empty()

    def set_enabled(self, key, enabled):
        """Additional gate on an action, on top of its needs_selection rule."""
        (self._disabled_keys.discard if enabled else self._disabled_keys.add)(key)
        self._sync_actions()

    def button(self, key):
        return self._buttons[key]

    # --- rendering ---

    def _visible_rows(self):
        needle = self._search.get().strip().casefold()
        rows = self._rows
        if needle:
            rows = [r for r in rows if any(needle in str(v).casefold() for v in r[1] if v is not None)]
        if self._sort_column is not None:
            index = int(self._sort_column[1:])
            rows = sorted(rows, key=lambda r: _sort_key(r[1][index]), reverse=self._sort_reverse)
        return rows

    def _render(self):
        selected = self.selected_id()
        self.tree.delete(*self.tree.get_children())
        rows = self._visible_rows()
        for row_id, values, status in rows:
            options = {"image": icon(status[0], 16, status[1])} if status else {}
            self.tree.insert("", "end", iid=row_id, values=[("" if v is None else v) for v in values], **options)

        total = len(self._rows)
        self.count_label.configure(text=str(total) if len(rows) == total else f"{len(rows)} of {total}")
        self._render_empty()

        if selected and self.tree.exists(selected):
            self.select(selected)
        elif self._auto_select and rows:
            self.select(rows[0][0])
        elif self._on_select:
            self._on_select()
        self._sync_actions()

    def _render_empty(self):
        if self.tree.get_children():
            self.empty_frame.place_forget()
            return
        if self._rows:  # rows exist, so the search filtered them all out
            content = ("zoom", "No matches", "Try a different search.", None)
        else:
            content = self._empty
        if content != self._rendered_empty:
            self._rendered_empty = content
            for child in self.empty_frame.winfo_children():
                child.destroy()
            icon_name, title, hint, action = content
            ttk.Label(self.empty_frame, image=icon(icon_name, 40, theme.DISABLED), style="Surface.TLabel").pack()
            ttk.Label(self.empty_frame, text=title, style="EmptyTitle.TLabel", justify="center").pack(pady=(px(10), 0))
            self._empty_hint = None
            if hint:
                self._empty_hint = ttk.Label(self.empty_frame, text=hint, style="SurfaceMuted.TLabel", justify="center")
                self._empty_hint.pack(pady=(px(4), 0))
                self._fit_empty_hint()
            if action:
                make_button(self.empty_frame, action[0], action[1], action[2], "primary").pack(pady=(px(12), 0))
        self.empty_frame.place(relx=0.5, rely=0.42, anchor="center")

    def _toggle_sort(self, name):
        if self._sort_column == name:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column, self._sort_reverse = name, False
        for column, heading in self._headings.items():
            arrow = (" ▼" if self._sort_reverse else " ▲") if column == name else ""
            self.tree.heading(column, text=heading + arrow)
        self._render()

    # --- events ---

    def _sync_actions(self):
        has_selection = self.selected_id() is not None
        for action in self._actions:
            key = action.key or action.text
            enabled = key not in self._disabled_keys and (has_selection or not action.needs_selection)
            self._buttons[key].state(["!disabled" if enabled else "disabled"])

    def _selection_changed(self):
        self._sync_actions()
        if self._on_select:
            self._on_select()

    def _on_double_click(self, event):
        if self.tree.identify_row(event.y) and self.tree.identify_region(event.x, event.y) in ("cell", "tree"):
            self._activate()

    def _activate(self):
        if self._on_activate and self.selected_id():
            self._on_activate()

    def _delete(self):
        if self._on_delete and self.selected_id():
            self._on_delete()


class ErrorBanner(ttk.Frame):
    """Inline error shown inside a dialog; collapsed until show() is called."""

    def __init__(self, parent):
        super().__init__(parent, style="Error.TFrame", padding=(px(10), px(8)))
        ttk.Label(self, image=icon("warning", 16, theme.DANGER), style="Error.TLabel").pack(side="left", anchor="n")
        self.message = ttk.Label(self, style="Error.TLabel", wraplength=px(390), justify="left")
        self.message.pack(side="left", padx=(px(8), 0), fill="x", expand=True)

    def show(self, text):
        self.message.configure(text=text)
        self.pack(fill="x", pady=(0, px(10)))


class Dialog(tk.Toplevel):
    """Modal dialog with a title, centered on its parent. Subclasses fill self.body, then call present()."""

    def __init__(self, parent, title):
        super().__init__(parent, background=theme.SURFACE)
        self.withdraw()  # stay hidden until sized and centered, to avoid a visible jump
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.body = ttk.Frame(self, style="Surface.TFrame", padding=px(20))
        self.body.pack(fill="both", expand=True)
        ttk.Label(self.body, text=title, style="DialogTitle.TLabel").pack(anchor="w", pady=(0, px(14)))
        self.banner_host = ttk.Frame(self.body, style="Surface.TFrame")
        self.banner_host.pack(fill="x")
        self.banner = ErrorBanner(self.banner_host)

    def show_failure(self, exc):
        """Validation problems stay in the dialog; anything unexpected gets the regular error box."""
        if isinstance(exc, ValidationError):
            self.banner.show(str(exc))
        elif isinstance(exc, sqlite3.IntegrityError):
            self.banner.show(f"The operation violates a database rule: {exc}")
        else:
            show_error(self, exc)

    def present(self, focus=None):
        self.update_idletasks()
        owner = self.master.winfo_toplevel()
        x = owner.winfo_rootx() + (owner.winfo_width() - self.winfo_reqwidth()) // 2
        y = owner.winfo_rooty() + (owner.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        (focus or self).focus_set()
        self.wait_window()


class FormDialog(Dialog):
    """Modal form.

    fields: list of dicts with keys: key, label, kind ('entry' | 'text' | 'check' | 'combo'),
    options (combo: list of (value, label)), height (text), hint (help text), required (marks the label).
    on_submit(values) may raise ValidationError to keep the dialog open.
    After closing, `result` holds the values dict (None if cancelled).
    """

    def __init__(self, parent, title, fields, initial=None, on_submit=None, submit_text="Save"):
        super().__init__(parent, title)
        self.result = None
        self._on_submit = on_submit
        self._widgets = {}
        initial = initial or {}

        form = ttk.Frame(self.body, style="Surface.TFrame")
        form.pack(fill="both", expand=True)
        first = None
        for field in fields:
            widget = self._add_field(form, field, initial.get(field["key"]))
            first = first or widget

        buttons = ttk.Frame(self.body, style="Surface.TFrame")
        buttons.pack(fill="x", pady=(px(8), 0))
        make_button(buttons, "Cancel", self.destroy).pack(side="right")
        make_button(buttons, submit_text, self._ok, kind="primary").pack(side="right", padx=(0, px(6)))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", self._on_return)

        self.present(first)

    def _add_field(self, form, field, value):
        key, kind = field["key"], field.get("kind", "entry")
        row = ttk.Frame(form, style="Surface.TFrame")
        row.pack(fill="x", pady=(0, px(12)))
        label = field["label"] + (" *" if field.get("required") else "")
        ttk.Label(row, text=label, style="SurfaceBold.TLabel").pack(anchor="w", pady=(0, px(3)))
        if kind == "text":
            widget = make_text(row, field.get("height", 4))
            if value:
                widget.insert("1.0", value)
            self._widgets[key] = (kind, widget, None)
        elif kind == "check":
            var = tk.BooleanVar(value=bool(value))
            widget = ttk.Checkbutton(row, variable=var, text=field.get("hint", ""))
            self._widgets[key] = (kind, var, None)
        elif kind == "combo":
            options = field["options"]
            widget = ttk.Combobox(row, values=[text for _, text in options], state="readonly", width=48)
            for index, (option_value, _) in enumerate(options):
                if option_value == value:
                    widget.current(index)
            if widget.current() < 0 and len(options) == 1:
                widget.current(0)
            self._widgets[key] = (kind, widget, options)
        else:
            var = tk.StringVar(value="" if value is None else str(value))
            widget = ttk.Entry(row, textvariable=var, width=52)
            self._widgets[key] = (kind, var, None)
        widget.pack(fill="x", anchor="w")
        if field.get("hint") and kind != "check":
            ttk.Label(row, text=field["hint"], style="SurfaceSmall.TLabel").pack(anchor="w", pady=(px(3), 0))
        return widget

    def _on_return(self, event):
        if isinstance(event.widget, tk.Text):
            return  # Enter is a new line there
        if isinstance(event.widget, ttk.Button):
            event.widget.invoke()
        else:
            self._ok()

    def values(self):
        values = {}
        for key, (kind, holder, options) in self._widgets.items():
            if kind == "text":
                values[key] = holder.get("1.0", "end").strip() or None
            elif kind == "check":
                values[key] = holder.get()
            elif kind == "combo":
                index = holder.current()
                values[key] = options[index][0] if index >= 0 else None
            else:
                values[key] = holder.get().strip() or None
        return values

    def _ok(self):
        values = self.values()
        if self._on_submit:
            try:
                self._on_submit(values)
            except Exception as exc:  # keep the dialog open on any save error
                self.show_failure(exc)
                return
        self.result = values
        self.destroy()
