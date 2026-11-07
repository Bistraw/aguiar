from tkinter import messagebox, ttk

from active_records import SettingActiveRecord
from services.qr_scanner import list_cameras
from ui.common import make_button
from ui.theme import px


def current_camera_index():
    try:
        return int(SettingActiveRecord.get_value(SettingActiveRecord.CAMERA_INDEX, "0"))
    except ValueError:
        return 0


class SettingsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        box = ttk.Frame(self, style="Card.TFrame", padding=px(18))
        box.pack(anchor="nw", fill="x")
        ttk.Label(box, text="Camera", style="Section.TLabel").pack(anchor="w")
        ttk.Label(box, text="Used to scan the answer cards during an interview. Changes are saved automatically.",
                  style="SurfaceMuted.TLabel").pack(anchor="w", pady=(px(2), px(12)))
        row = ttk.Frame(box, style="Surface.TFrame")
        row.pack(anchor="w")
        self.combo = ttk.Combobox(row, state="readonly", width=24)
        self.combo.pack(side="left")
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.save())
        make_button(row, "Detect cameras", self.detect, "video").pack(side="left", padx=(px(8), 0))
        self.status = ttk.Label(box, style="SurfaceMuted.TLabel")
        self.status.pack(anchor="w", pady=(px(10), 0))
        self._indexes = []

        credits_box = ttk.Frame(self, padding=(px(2), px(12)))
        credits_box.pack(anchor="w")
        ttk.Label(credits_box, text="Icons: Game Icons by Kenney (www.kenney.nl), CC0.", style="Muted.TLabel").pack()

    def refresh(self):
        index = current_camera_index()
        if index not in self._indexes:
            self._indexes = sorted(set(self._indexes) | {index})
        self._fill(index)
        self.status.configure(text=f"Current: Camera {index}")

    def _fill(self, selected):
        self.combo.configure(values=[f"Camera {i}" for i in self._indexes])
        if selected in self._indexes:
            self.combo.current(self._indexes.index(selected))

    def detect(self):
        self.status.configure(text="Detecting cameras…")
        self.winfo_toplevel().configure(cursor="watch")
        self.update_idletasks()
        try:
            found = list_cameras()
        finally:
            self.winfo_toplevel().configure(cursor="")
        if not found:
            self.status.configure(text="No camera detected.")
            messagebox.showwarning("Camera", "No camera detected.", parent=self)
            return
        self._indexes = found
        current = current_camera_index()
        self._fill(current if current in found else found[0])
        self.status.configure(text=f"Detected: {', '.join(f'Camera {i}' for i in found)}")
        if current not in found:
            self.save()

    def save(self):
        index = self.combo.current()
        if index < 0:
            return
        SettingActiveRecord.set_value(SettingActiveRecord.CAMERA_INDEX, self._indexes[index])
        self.status.configure(text=f"Saved. Current: Camera {self._indexes[index]}")
