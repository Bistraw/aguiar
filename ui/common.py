"""Shared Tkinter widgets and helpers."""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from active_records import ValidationError

FONT = ("Segoe UI", 10)


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


class ListPanel(ttk.LabelFrame):
    """Treeview with a scrollbar and a button row. Row iids are record ids."""

    def __init__(self, parent, title, columns, buttons, on_select=None, on_activate=None):
        super().__init__(parent, text=title, padding=6)
        self._on_select = on_select
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True)
        names = [f"c{i}" for i in range(len(columns))]
        self.tree = ttk.Treeview(tree_frame, columns=names, show="headings", selectmode="browse")
        for name, (heading, width) in zip(names, columns):
            self.tree.heading(name, text=heading, anchor="w")
            self.tree.column(name, width=width, anchor="w", stretch=True)
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        button_row = ttk.Frame(self)
        button_row.pack(fill="x", pady=(6, 0))
        for text, command in buttons:
            ttk.Button(button_row, text=text, command=command).pack(side="left", padx=(0, 4))

        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_select and self._on_select())
        if on_activate:
            self.tree.bind("<Double-1>", lambda e: on_activate())

    def set_rows(self, rows):
        """rows: iterable of (id, values). Keeps the selection when the id is still present."""
        selected = self.selected_id()
        self.tree.delete(*self.tree.get_children())
        for row_id, values in rows:
            self.tree.insert("", "end", iid=row_id, values=[("" if v is None else v) for v in values])
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
            self.tree.see(selected)
        elif self._on_select:
            self._on_select()

    def selected_id(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def select(self, row_id):
        if row_id and self.tree.exists(row_id):
            self.tree.selection_set(row_id)
            self.tree.see(row_id)


class FormDialog(tk.Toplevel):
    """Modal form.

    fields: list of dicts with keys: key, label, kind ('entry' | 'text' | 'check' | 'combo'),
    options (combo: list of (value, label)), height (text).
    on_submit(values) may raise ValidationError to keep the dialog open.
    After closing, `result` holds the values dict (None if cancelled).
    """

    def __init__(self, parent, title, fields, initial=None, on_submit=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.result = None
        self._on_submit = on_submit
        self._widgets = {}
        initial = initial or {}

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        first = None
        for row, field in enumerate(fields):
            key, kind = field["key"], field.get("kind", "entry")
            value = initial.get(key)
            ttk.Label(body, text=field["label"]).grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=4)
            if kind == "text":
                widget = tk.Text(body, width=50, height=field.get("height", 4), wrap="word", font=FONT)
                if value:
                    widget.insert("1.0", value)
                self._widgets[key] = (kind, widget, None)
            elif kind == "check":
                var = tk.BooleanVar(value=bool(value))
                widget = ttk.Checkbutton(body, variable=var)
                self._widgets[key] = (kind, var, None)
            elif kind == "combo":
                options = field["options"]
                widget = ttk.Combobox(body, values=[label for _, label in options], state="readonly", width=48)
                for index, (option_value, _) in enumerate(options):
                    if option_value == value:
                        widget.current(index)
                self._widgets[key] = (kind, widget, options)
            else:
                var = tk.StringVar(value="" if value is None else str(value))
                widget = ttk.Entry(body, textvariable=var, width=52)
                self._widgets[key] = (kind, var, None)
            widget.grid(row=row, column=1, sticky="we", pady=4)
            first = first or widget

        buttons = ttk.Frame(body)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="OK", command=self._ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())

        self.grab_set()
        if first is not None:
            first.focus_set()
        self.wait_window()

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
                show_error(self, exc)
                return
        self.result = values
        self.destroy()
