from tkinter import messagebox, ttk

from active_records import SettingActiveRecord
from services.qr_scanner import list_cameras


def current_camera_index():
    try:
        return int(SettingActiveRecord.get_value(SettingActiveRecord.CAMERA_INDEX, "0"))
    except ValueError:
        return 0


class SettingsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        box = ttk.LabelFrame(self, text="Camera", padding=12)
        box.pack(anchor="nw", fill="x")
        ttk.Label(box, text="Camera used to scan the cards:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.combo = ttk.Combobox(box, state="readonly", width=20)
        self.combo.grid(row=0, column=1, sticky="w")
        ttk.Button(box, text="Detect cameras", command=self.detect).grid(row=0, column=2, padx=8)
        ttk.Button(box, text="Save", command=self.save).grid(row=0, column=3)
        self.status = ttk.Label(box, text="", foreground="gray")
        self.status.grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self._indexes = []

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
        self.update_idletasks()
        found = list_cameras()
        if not found:
            self.status.configure(text="No camera detected.")
            messagebox.showwarning("Camera", "No camera detected.", parent=self)
            return
        self._indexes = found
        current = current_camera_index()
        self._fill(current if current in found else found[0])
        self.status.configure(text=f"Detected: {', '.join(f'Camera {i}' for i in found)}")

    def save(self):
        index = self.combo.current()
        if index < 0:
            return
        SettingActiveRecord.set_value(SettingActiveRecord.CAMERA_INDEX, self._indexes[index])
        self.status.configure(text=f"Saved. Current: Camera {self._indexes[index]}")
