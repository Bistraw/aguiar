from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from active_records import CardActiveRecord
from services.qr_export import build_card_image, export_card_qr_png
from ui import theme
from ui.common import Action, FormDialog, ListPanel, confirm, make_button, run_action
from ui.icons import icon
from ui.theme import px

PREVIEW_SIDE = 260


class CardsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._photo = None
        self.list = ListPanel(
            self,
            "All cards",
            [("Name", 300)],
            [
                Action("New card", self.new, "plus", "primary", needs_selection=False),
                Action("Rename", self.edit, "wrench"),
                Action("Delete", self.delete, "trashcan", "danger"),
            ],
            on_select=self._render_preview,
            on_activate=self.edit,
            on_delete=self.delete,
            searchable=True,
        )
        self.list.set_empty("menuGrid", "No cards yet", "Cards are the physical answers patients show to the camera.",
                            ("New card", self.new, "plus"))
        self.list.pack(side="left", fill="both", expand=True)
        self._build_preview()

    def _build_preview(self):
        panel = ttk.Frame(self, style="Card.TFrame", padding=px(14))
        panel.pack(side="right", fill="y", padx=(px(12), 0))
        ttk.Label(panel, text="Printable QR", style="Section.TLabel").pack(anchor="w")
        ttk.Label(panel, text="Print it and glue it to the physical card.", style="SurfaceMuted.TLabel").pack(
            anchor="w", pady=(px(2), px(12)))
        self.preview = ttk.Label(panel, style="SurfaceMuted.TLabel", anchor="center", justify="center",
                                 compound="top", width=34)
        self.preview.pack(fill="x", ipady=px(6))
        self.export_button = make_button(panel, "Export QR…", self.export_qr, "export")
        self.export_button.pack(fill="x", pady=(px(12), 0))

    def refresh(self):
        self.list.set_rows((c.id, [c.name]) for c in CardActiveRecord.all())
        self._render_preview()

    def _render_preview(self):
        card = CardActiveRecord.get(self.list.selected_id())
        if card is None:
            self._photo = None
            self.preview.configure(image=icon("target", 40, theme.DISABLED), text="\nSelect a card to see its QR",
                                   width=34)
            self.export_button.state(["disabled"])
            return
        image = build_card_image(card)
        image.thumbnail((px(PREVIEW_SIDE), px(PREVIEW_SIDE)))
        self._photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self._photo, text="", width=0)
        self.export_button.state(["!disabled"])

    def _selected(self):
        card = CardActiveRecord.get(self.list.selected_id())
        if card is None:
            messagebox.showinfo("Cards", "Select a card first.", parent=self)
        return card

    def _form(self, title, card):
        def submit(values):
            card.name = values["name"]
            card.save()

        fields = [{"key": "name", "label": "Name", "required": True, "hint": "For example: Happy, Sad, Angry."}]
        dialog = FormDialog(self, title, fields, {"name": card.name}, submit)
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
