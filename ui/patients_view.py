from datetime import date
from tkinter import messagebox, ttk

from active_records import PatientActiveRecord
from ui.common import Action, FormDialog, ListPanel, confirm, run_action, short

FIELDS = [
    {"key": "name", "label": "Name", "required": True},
    {"key": "birth_date", "label": "Birth date", "hint": "Format: YYYY-MM-DD. Optional; used to compute the age."},
    {"key": "description", "label": "Description", "kind": "text", "height": 5},
]


class PatientsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.list = ListPanel(
            self,
            "All patients",
            [("Name", 240), ("Birth date", 110, False), ("Age", 70, False), ("Description", 400)],
            [
                Action("New patient", self.new, "plus", "primary", needs_selection=False),
                Action("Edit", self.edit, "wrench"),
                Action("Delete", self.delete, "trashcan", "danger"),
            ],
            on_activate=self.edit,
            on_delete=self.delete,
            searchable=True,
        )
        self.list.set_empty("singleplayer", "No patients yet", "Add a patient to be able to create interviews.",
                            ("New patient", self.new, "plus"))
        self.list.pack(fill="both", expand=True)

    def refresh(self):
        today = date.today()
        self.list.set_rows(
            (p.id, [p.name, p.birth_date, p.age_at(today), short(p.description, 80)])
            for p in PatientActiveRecord.all()
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
