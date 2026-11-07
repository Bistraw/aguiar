"""Tinted, DPI-scaled icons from assets/icons (Kenney Game Icons, CC0). Results are cached for the app's lifetime."""

import os
from functools import lru_cache

from PIL import Image, ImageTk

from db import _resource_dir
from ui import theme

ASSETS_DIR = os.path.join(_resource_dir(), "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")


@lru_cache(maxsize=None)
def icon(name, size=16, color=theme.TEXT):
    """PhotoImage of the named icon: the source's alpha channel filled with `color`."""
    side = theme.px(size)
    with Image.open(os.path.join(ICONS_DIR, f"{name}.png")) as source:
        alpha = source.convert("RGBA").getchannel("A").resize((side, side), Image.LANCZOS)
    tinted = Image.new("RGBA", (side, side), color)
    tinted.putalpha(alpha)
    return ImageTk.PhotoImage(tinted)


def button_icon(name, size=16, color=theme.TEXT):
    """Value for a ttk `image` option: the icon, grayed out while the widget is disabled."""
    return (icon(name, size, color), "disabled", icon(name, size, theme.DISABLED))


def app_icon():
    with Image.open(os.path.join(ASSETS_DIR, "app.png")) as source:
        return ImageTk.PhotoImage(source.convert("RGBA"))
