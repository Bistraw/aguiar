import tkinter as tk
from tkinter import ttk

from ui.banks_view import BanksView
from ui.cards_view import CardsView
from ui.common import FONT
from ui.interviews_view import InterviewsView
from ui.patients_view import PatientsView
from ui.settings_view import SettingsView

APP_TITLE = "Interview Assistant"


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x700")
        self.minsize(900, 500)
        self.option_add("*Font", FONT)
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=24)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)
        self.views = [
            (InterviewsView(self.notebook), "Interviews"),
            (BanksView(self.notebook), "Question banks"),
            (CardsView(self.notebook), "Cards"),
            (PatientsView(self.notebook), "Patients"),
            (SettingsView(self.notebook), "Settings"),
        ]
        for view, title in self.views:
            self.notebook.add(view, text=title)
        # Each tab reloads its data when shown, so changes made in other tabs are visible.
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._current_view().refresh())
        self.after_idle(lambda: self._current_view().refresh())

    def _current_view(self):
        return self.views[self.notebook.index(self.notebook.select())][0]
