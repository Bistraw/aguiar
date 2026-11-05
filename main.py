import sys

import db
from ui.main_window import MainWindow


def _enable_dpi_awareness():
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def main():
    _enable_dpi_awareness()
    db.init_schema()
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
