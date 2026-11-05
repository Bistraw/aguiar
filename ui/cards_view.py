from tkinter import filedialog, messagebox, ttk

from active_records import CardActiveRecord
from services.qr_export import export_card_qr_png
from ui.common import FormDialog, ListPanel, confirm, run_action


class CardsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=8)
        self.list = ListPanel(
            self,
            "Cards",
            [("Name", 300)],
            [("New", self.new), ("Rename", self.edit), ("Delete", self.delete), ("Export QR…", self.export_qr)],
            on_activate=self.edit,
        )
        self.list.pack(fill="both", expand=True)

    def refresh(self):
        self.list.set_rows((c.id, [c.name]) for c in CardActiveRecord.all())

    def _selected(self):
        card = CardActiveRecord.get(self.list.selected_id())
        if card is None:
            messagebox.showinfo("Cards", "Select a card first.", parent=self)
        return card

    def _form(self, title, card):
        def submit(values):
            card.name = values["name"]
            card.save()

        dialog = FormDialog(self, title, [{"key": "name", "label": "Name"}], {"name": card.name}, submit)
        if dialog.result is not None:
            self.refresh()
            self.list.select(card.id)

    def new(self):
        self._form("New card", CardActiveRecord())

    def edit(self):
        card = self._selected()
        if card:
            self._form("Rename card", card)

    def delete(self):
        card = self._selected()
        if card and confirm(self, f"Delete card '{card.name}'?"):
            if run_action(self, card.delete):
                self.refresh()

    def export_qr(self):
        card = self._selected()
        if not card:
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export QR",
            defaultextension=".png",
            initialfile=f"card_{card.name}.png",
            filetypes=[("PNG image", "*.png")],
        )
        if path and run_action(self, lambda: export_card_qr_png(card, path)):
            messagebox.showinfo("Export QR", f"QR saved to:\n{path}", parent=self)
