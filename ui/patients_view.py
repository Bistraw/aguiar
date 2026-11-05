from tkinter import messagebox, ttk

from active_records import PatientActiveRecord
from ui.common import FormDialog, ListPanel, confirm, run_action, short

FIELDS = [
    {"key": "name", "label": "Name"},
    {"key": "birth_date", "label": "Birth date (YYYY-MM-DD)"},
    {"key": "description", "label": "Description", "kind": "text", "height": 5},
]


class PatientsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=8)
        self.list = ListPanel(
            self,
            "Patients",
            [("Name", 220), ("Birth date", 110), ("Description", 400)],
            [("New", self.new), ("Edit", self.edit), ("Delete", self.delete)],
            on_activate=self.edit,
        )
        self.list.pack(fill="both", expand=True)

    def refresh(self):
        self.list.set_rows(
            (p.id, [p.name, p.birth_date, short(p.description, 80)]) for p in PatientActiveRecord.all()
        )

    def _selected(self):
        patient = PatientActiveRecord.get(self.list.selected_id())
        if patient is None:
            messagebox.showinfo("Patients", "Select a patient first.", parent=self)
        return patient

    def _form(self, title, patient):
        def submit(values):
            patient.name = values["name"]
            patient.birth_date = values["birth_date"]
            patient.description = values["description"]
            patient.save()

        initial = {"name": patient.name, "birth_date": patient.birth_date, "description": patient.description}
        if FormDialog(self, title, FIELDS, initial, submit).result is not None:
            self.refresh()
            self.list.select(patient.id)

    def new(self):
        self._form("New patient", PatientActiveRecord())

    def edit(self):
        patient = self._selected()
        if patient:
            self._form("Edit patient", patient)

    def delete(self):
        patient = self._selected()
        if patient and confirm(self, f"Delete patient '{patient.name}'?"):
            if run_action(self, patient.delete):
                self.refresh()
