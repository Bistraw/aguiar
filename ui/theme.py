"""Colors, fonts and ttk styles. All look-and-feel decisions live here."""

from tkinter import ttk

# Palette (text colors keep at least 4.5:1 contrast on their backgrounds).
BG = "#F3F5F6"
SURFACE = "#FFFFFF"
BORDER = "#D8DEE3"
TEXT = "#1F2933"
MUTED = "#5B6770"
DISABLED = "#98A2AA"
DISABLED_BG = "#E9ECEE"
ACCENT = "#0F766E"
ACCENT_HOVER = "#0B5F58"
ACCENT_SOFT = "#D9EFEC"
HOVER = "#EEF1F3"
DANGER = "#B42318"
DANGER_SOFT = "#FDECEA"
WARNING = "#B54708"
SUCCESS = "#067647"
SIDEBAR = "#17313B"
SIDEBAR_HOVER = "#21424E"
SIDEBAR_ACTIVE = "#2B5361"
SIDEBAR_TEXT = "#D5E1E5"
WHITE = "#FFFFFF"

FAMILY = "Segoe UI"
FONT = (FAMILY, 10)
FONT_SMALL = (FAMILY, 9)
FONT_BOLD = (FAMILY, 10, "bold")
FONT_SECTION = (FAMILY, 12, "bold")
FONT_DIALOG_TITLE = (FAMILY, 14, "bold")
FONT_PAGE_TITLE = (FAMILY, 18, "bold")
FONT_BRAND = (FAMILY, 12, "bold")
FONT_PATIENT_HINT = (FAMILY, 14)
FONT_QUESTION = (FAMILY, 30)
FONT_QUESTION_LONG = (FAMILY, 24)
FONT_FEEDBACK = (FAMILY, 26)
FONT_FINISH = (FAMILY, 28, "bold")

_scale = 1.0


def px(value):
    """Scale a pixel size to the screen DPI (fonts in points scale on their own)."""
    return round(value * _scale)


def apply_theme(root):
    global _scale
    _scale = root.winfo_fpixels("1i") / 96
    root.configure(background=BG)
    # Fonts of ttk widgets come from the styles below. A global "*Font" option would override them.
    root.option_add("*TCombobox*Listbox.font", f"{{{FAMILY}}} 10")
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", WHITE)
    root.option_add("*TCombobox*Listbox.relief", "flat")

    style = ttk.Style(root)
    style.theme_use("clam")  # the only built-in theme that honors custom colors everywhere
    style.configure(".", background=BG, foreground=TEXT, font=FONT, bordercolor=BORDER, focuscolor=ACCENT,
                    lightcolor=BG, darkcolor=BG, troughcolor=BG)

    _frames_and_labels(style)
    _buttons(style)
    _inputs(style)
    _lists(style)
    _navigation(style)


def _frames_and_labels(style):
    style.configure("Surface.TFrame", background=SURFACE)
    style.configure("Card.TFrame", background=SURFACE, bordercolor=BORDER, relief="solid", borderwidth=1)
    style.configure("Sidebar.TFrame", background=SIDEBAR)

    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("PageTitle.TLabel", font=FONT_PAGE_TITLE)
    style.configure("Brand.TLabel", background=SIDEBAR, foreground=WHITE, font=FONT_BRAND)
    style.configure("SidebarNote.TLabel", background=SIDEBAR, foreground=SIDEBAR_TEXT, font=FONT_SMALL)

    style.configure("Surface.TLabel", background=SURFACE)
    style.configure("SurfaceBold.TLabel", background=SURFACE, font=FONT_BOLD)
    style.configure("SurfaceMuted.TLabel", background=SURFACE, foreground=MUTED)
    style.configure("SurfaceSmall.TLabel", background=SURFACE, foreground=MUTED, font=FONT_SMALL)
    style.configure("Section.TLabel", background=SURFACE, font=FONT_SECTION)
    style.configure("DialogTitle.TLabel", background=SURFACE, font=FONT_DIALOG_TITLE)
    style.configure("EmptyTitle.TLabel", background=SURFACE, foreground=TEXT, font=FONT_SECTION)
    style.configure("Finish.TLabel", background=SURFACE, font=FONT_FINISH)
    style.configure("PatientHint.TLabel", background=SURFACE, foreground=MUTED, font=FONT_PATIENT_HINT)

    style.configure("Error.TFrame", background=DANGER_SOFT)
    style.configure("Error.TLabel", background=DANGER_SOFT, foreground=DANGER)


def _buttons(style):
    padding = (px(12), px(6))
    style.configure("TButton", background=SURFACE, foreground=TEXT, padding=padding, relief="raised", borderwidth=1,
                    bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE, focuscolor=SURFACE,
                    focusthickness=0, anchor="center", width=0)
    style.map("TButton",
              background=[("disabled", SURFACE), ("pressed", BORDER), ("active", HOVER)],
              foreground=[("disabled", DISABLED)],
              lightcolor=[("disabled", SURFACE), ("pressed", BORDER), ("active", HOVER)],
              darkcolor=[("disabled", SURFACE), ("pressed", BORDER), ("active", HOVER)],
              bordercolor=[("focus", ACCENT)])

    style.configure("Primary.TButton", background=ACCENT, foreground=WHITE, bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, focuscolor=ACCENT, font=FONT_BOLD)
    style.map("Primary.TButton",
              background=[("disabled", DISABLED_BG), ("pressed", ACCENT_HOVER), ("active", ACCENT_HOVER)],
              foreground=[("disabled", DISABLED)],
              lightcolor=[("disabled", DISABLED_BG), ("pressed", ACCENT_HOVER), ("active", ACCENT_HOVER)],
              darkcolor=[("disabled", DISABLED_BG), ("pressed", ACCENT_HOVER), ("active", ACCENT_HOVER)],
              bordercolor=[("disabled", DISABLED_BG), ("focus", TEXT)])

    style.configure("Danger.TButton", foreground=DANGER)
    style.map("Danger.TButton",
              background=[("disabled", SURFACE), ("pressed", BORDER), ("active", DANGER_SOFT)],
              foreground=[("disabled", DISABLED)],
              lightcolor=[("disabled", SURFACE), ("active", DANGER_SOFT)],
              darkcolor=[("disabled", SURFACE), ("active", DANGER_SOFT)],
              bordercolor=[("focus", DANGER)])

    # Discreet psychologist controls on the interview screen.
    style.configure("Quiet.TButton", foreground=MUTED, font=FONT_SMALL, padding=(px(8), px(4)))


def _inputs(style):
    field = {"fieldbackground": SURFACE, "background": SURFACE, "foreground": TEXT, "bordercolor": BORDER,
             "lightcolor": SURFACE, "darkcolor": SURFACE, "padding": px(5), "insertcolor": TEXT}
    style.configure("TEntry", **field)
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", SURFACE)],
              darkcolor=[("focus", SURFACE)])
    style.configure("TCombobox", arrowcolor=MUTED, arrowsize=px(14), **field)
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE)], background=[("active", HOVER)],
              foreground=[("readonly", TEXT)], selectbackground=[("readonly", SURFACE)],
              selectforeground=[("readonly", TEXT)], bordercolor=[("focus", ACCENT)],
              lightcolor=[("focus", SURFACE)], darkcolor=[("focus", SURFACE)])
    style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, focuscolor=SURFACE,
                    indicatorcolor=SURFACE, indicatorbackground=SURFACE, upperbordercolor=BORDER,
                    lowerbordercolor=BORDER, padding=(0, px(2)))
    style.map("TCheckbutton", background=[("active", SURFACE)],
              indicatorcolor=[("selected", ACCENT), ("pressed", ACCENT_SOFT)])



def _lists(style):
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT, rowheight=px(30),
                    borderwidth=0, relief="flat", lightcolor=SURFACE, darkcolor=SURFACE, bordercolor=SURFACE)
    style.map("Treeview", background=[("selected", ACCENT_SOFT)], foreground=[("selected", TEXT)])
    # No expander arrow: every list is flat, and the arrow would push the status icon to the right.
    style.layout("Treeview.Item", [("Treeitem.padding", {"sticky": "nswe", "children": [
        ("Treeitem.image", {"side": "left", "sticky": ""}),
        ("Treeitem.text", {"side": "left", "sticky": ""}),
    ]})])
    style.configure("Treeview.Heading", background=SURFACE, foreground=MUTED, font=FONT_SMALL, relief="flat",
                    padding=(px(6), px(6)), borderwidth=0, lightcolor=SURFACE, darkcolor=SURFACE, bordercolor=BORDER)
    style.map("Treeview.Heading", background=[("active", HOVER)], foreground=[("active", TEXT)],
              lightcolor=[("active", HOVER)], darkcolor=[("active", HOVER)])
    style.configure("TScrollbar", background=BORDER, troughcolor=SURFACE, bordercolor=SURFACE, arrowcolor=MUTED,
                    lightcolor=BORDER, darkcolor=BORDER, relief="flat", arrowsize=px(12), gripcount=0)
    style.map("TScrollbar", background=[("disabled", SURFACE), ("active", DISABLED)],
              lightcolor=[("disabled", SURFACE)], darkcolor=[("disabled", SURFACE)],
              arrowcolor=[("disabled", SURFACE)])
    style.configure("TPanedwindow", background=BG)
    style.configure("Sash", sashthickness=px(12), gripcount=0, background=BG, lightcolor=BG, darkcolor=BG,
                    bordercolor=BG)


def _navigation(style):
    style.configure("Nav.Toolbutton", background=SIDEBAR, foreground=SIDEBAR_TEXT, font=FONT, anchor="w",
                    padding=(px(14), px(10)), relief="flat", borderwidth=0, lightcolor=SIDEBAR, darkcolor=SIDEBAR,
                    bordercolor=SIDEBAR, focuscolor=SIDEBAR)
    states = [("selected", SIDEBAR_ACTIVE), ("active", SIDEBAR_HOVER)]
    style.map("Nav.Toolbutton", background=states, lightcolor=states, darkcolor=states, bordercolor=states,
              foreground=[("selected", WHITE), ("active", WHITE)])
