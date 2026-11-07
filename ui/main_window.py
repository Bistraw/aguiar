import tkinter as tk
from tkinter import ttk

from ui import theme
from ui.banks_view import BanksView
from ui.cards_view import CardsView
from ui.icons import app_icon, icon
from ui.interviews_view import InterviewsView
from ui.patients_view import PatientsView
from ui.settings_view import SettingsView
from ui.theme import px

APP_TITLE = "Interview Assistant"

# view class, navigation label, icon, subtitle
PAGES = [
    (InterviewsView, "Interviews", "multiplayer", "Create, run and export evaluation sessions."),
    (BanksView, "Question banks", "question", "Pick a bank, then a question, to manage its candidate answers."),
    (CardsView, "Cards", "menuGrid", "Physical answer cards and their printable QR codes."),
    (PatientsView, "Patients", "singleplayer", "People who take part in the interviews."),
    (SettingsView, "Settings", "gear", "Application preferences."),
]


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        theme.apply_theme(self)
        self.geometry(f"{px(1240)}x{px(760)}")
        self.minsize(px(1180), px(600))
        self._app_icon = app_icon()
        self.iconphoto(True, self._app_icon)

        self._page = tk.IntVar(value=0)
        self._build_sidebar()
        content = ttk.Frame(self, padding=(px(24), px(18), px(24), px(20)))
        content.pack(side="left", fill="both", expand=True)
        self.page_title = ttk.Label(content, style="PageTitle.TLabel")
        self.page_title.pack(anchor="w")
        self.page_subtitle = ttk.Label(content, style="Muted.TLabel")
        self.page_subtitle.pack(anchor="w", pady=(px(2), px(14)))
        self.views = [page[0](content) for page in PAGES]
        for index in range(len(PAGES)):
            self.bind(f"<Control-Key-{index + 1}>", lambda e, i=index: self.show_page(i))
        self.after_idle(lambda: self.show_page(0))

    def _build_sidebar(self):
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=px(210))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = ttk.Frame(sidebar, style="Sidebar.TFrame", padding=(px(14), px(18), px(14), px(16)))
        brand.pack(fill="x")
        ttk.Label(brand, image=icon("multiplayer", 22, theme.WHITE), style="Brand.TLabel").pack(side="left")
        ttk.Label(brand, text=APP_TITLE, style="Brand.TLabel").pack(side="left", padx=(px(8), 0))
        for index, (_, label, icon_name, _) in enumerate(PAGES):
            image = (icon(icon_name, 18, theme.SIDEBAR_TEXT), "selected", icon(icon_name, 18, theme.WHITE))
            ttk.Radiobutton(sidebar, text=f"  {label}", image=image, compound="left", style="Nav.Toolbutton",
                            variable=self._page, value=index,
                            command=lambda i=index: self.show_page(i)).pack(fill="x")

    def show_page(self, index):
        self._page.set(index)
        for view in self.views:
            view.pack_forget()
        _, label, _, subtitle = PAGES[index]
        self.page_title.configure(text=label)
        self.page_subtitle.configure(text=subtitle)
        view = self.views[index]
        view.pack(fill="both", expand=True)
        # Each page reloads its data when shown, so changes made in other pages are visible.
        view.refresh()
