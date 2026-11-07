from tkinter import messagebox, ttk

from active_records import (
    InterviewActiveRecord,
    InterviewStatus,
    PatientActiveRecord,
    QuestionBankActiveRecord,
    ValidationError,
)
from services.interview_service import create_interview, list_interviews
from ui import theme
from ui.common import Action, FormDialog, ListPanel, confirm, format_datetime, run_action
from ui.interview_screen import export_csv_dialog, open_interview_screen

STATUS_DISPLAY = {
    InterviewStatus.CREATED: ("Not started", "right", theme.MUTED),
    InterviewStatus.IN_PROGRESS: ("In progress", "next", theme.ACCENT),
    InterviewStatus.PAUSED: ("Paused", "pause", theme.WARNING),
    InterviewStatus.COMPLETED: ("Completed", "checkmark", theme.SUCCESS),
    InterviewStatus.ABORTED: ("Ended early", "stop", theme.MUTED),
}


class InterviewsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.list = ListPanel(
            self,
            "All interviews",
            [("Patient", 190), ("Bank", 190), ("Status", 110, False), ("Started", 130, False),
             ("Ended", 130, False), ("Progress", 80, False)],
            [
                Action("New interview", self.new, "plus", "primary", needs_selection=False),
                Action("Start", self.start, "next", key="start"),
                Action("Export CSV", self.export, "export"),
                Action("Delete", self.delete, "trashcan", "danger"),
            ],
            on_select=self._update_start_button,
            on_activate=self.start,
            on_delete=self.delete,
            searchable=True,
            status_column=True,
        )
        self.list.set_empty("multiplayer", "No interviews yet",
                            "Create one by choosing a patient and a question bank.",
                            ("New interview", self.new, "plus"))
        self.list.pack(fill="both", expand=True)
        self._statuses = {}

    def refresh(self):
        rows = list_interviews()
        self._statuses = {r["Id"]: r["Status"] for r in rows}
        self.list.set_rows(self._row(r) for r in rows)
        self._update_start_button()

    @staticmethod
    def _row(r):
        label, icon_name, color = STATUS_DISPLAY[r["Status"]]
        values = [r["PatientName"], r["BankName"], label, format_datetime(r["Start"]),
                  format_datetime(r["End"]), f'{r["Answered"]} / {r["Total"]}']
        return r["Id"], values, (icon_name, color)

    def _update_start_button(self):
        status = self._statuses.get(self.list.selected_id())
        self.list.button("start").configure(text=" Resume" if status in (InterviewStatus.PAUSED,
                                                                         InterviewStatus.IN_PROGRESS) else " Start")
        self.list.set_enabled("start", status not in InterviewStatus.FINISHED)

    def _selected(self):
        interview = InterviewActiveRecord.get(self.list.selected_id())
        if interview is None:
            messagebox.showinfo("Interviews", "Select an interview first.", parent=self)
        return interview

    def new(self):
        patients = PatientActiveRecord.all()
        banks = QuestionBankActiveRecord.all()
        missing = [name for name, records in (("patient", patients), ("question bank", banks)) if not records]
        if missing:
            needed = " and one ".join(missing)
            messagebox.showinfo("New interview", f"Create at least one {needed} first.", parent=self)
            return
        fields = [
            {"key": "patient_id", "label": "Patient", "kind": "combo", "required": True,
             "options": [(p.id, p.name) for p in patients]},
            {"key": "bank_id", "label": "Question bank", "kind": "combo", "required": True,
             "options": [(b.id, _bank_label(b)) for b in banks]},
            {"key": "answer_limit", "label": "Time limit per question",
             "hint": "In seconds. Leave blank for no limit."},
            {"key": "give_feedback", "label": "Feedback", "kind": "check",
             "hint": "Show the answer's feedback text after each answer"},
        ]
        created = {}

        def submit(values):
            limit = values["answer_limit"]
            if limit is not None:
                try:
                    limit = int(limit)
                except ValueError:
                    raise ValidationError("The time limit must be a whole number of seconds.")
            if not values["patient_id"]:
                raise ValidationError("A patient is required.")
            created["interview"] = create_interview(
                values["patient_id"], values["bank_id"], values["give_feedback"], limit
            )

        FormDialog(self, "New interview", fields, {"give_feedback": False}, submit, submit_text="Create")
        interview = created.get("interview")
        if interview:
            self.refresh()
            self.list.select(interview.id)
            if messagebox.askyesno("New interview", "Interview created. Start it now?", parent=self):
                self._open(interview)

    def start(self):
        interview = self._selected()
        if not interview:
            return
        if interview.status in InterviewStatus.FINISHED:
            messagebox.showinfo("Interviews", "This interview is already finished.", parent=self)
            return
        self._open(interview)

    def _open(self, interview):
        open_interview_screen(self, interview.id, on_close=self.refresh)

    def export(self):
        interview = self._selected()
        if interview:
            export_csv_dialog(self, interview)

    def delete(self):
        interview = self._selected()
        if interview and confirm(self, "Delete the selected interview and all its answers?"):
            if run_action(self, interview.delete):
                self.refresh()


def _bank_label(bank):
    count = len(bank.questions())
    return f"{bank.name} ({count} question{'' if count == 1 else 's'})"
