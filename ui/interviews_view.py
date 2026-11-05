from tkinter import messagebox, ttk

from active_records import (
    InterviewActiveRecord,
    InterviewStatus,
    PatientActiveRecord,
    QuestionBankActiveRecord,
    ValidationError,
)
from services.interview_service import create_interview, list_interviews
from ui.common import FormDialog, ListPanel, confirm, format_datetime, run_action
from ui.interview_screen import export_csv_dialog, open_interview_screen


class InterviewsView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=8)
        self.list = ListPanel(
            self,
            "Interviews",
            [("Patient", 180), ("Bank", 180), ("Status", 90), ("Started", 130), ("Ended", 130), ("Progress", 80)],
            [("New", self.new), ("Start / Resume", self.start), ("Export CSV", self.export), ("Delete", self.delete)],
            on_activate=self.start,
        )
        self.list.pack(fill="both", expand=True)

    def refresh(self):
        self.list.set_rows(
            (r["Id"], [r["PatientName"], r["BankName"], r["Status"], format_datetime(r["Start"]),
                       format_datetime(r["End"]), f'{r["Answered"]}/{r["Total"]}'])
            for r in list_interviews()
        )

    def _selected(self):
        interview = InterviewActiveRecord.get(self.list.selected_id())
        if interview is None:
            messagebox.showinfo("Interviews", "Select an interview first.", parent=self)
        return interview

    def new(self):
        patients = PatientActiveRecord.all()
        banks = QuestionBankActiveRecord.all()
        if not patients or not banks:
            messagebox.showinfo("Interviews", "Create at least one patient and one question bank first.", parent=self)
            return
        fields = [
            {"key": "patient_id", "label": "Patient", "kind": "combo", "options": [(p.id, p.name) for p in patients]},
            {"key": "bank_id", "label": "Question bank", "kind": "combo", "options": [(b.id, b.name) for b in banks]},
            {"key": "give_feedback", "label": "Show feedback", "kind": "check"},
            {"key": "answer_limit", "label": "Timeout per question\n(seconds, blank = none)"},
        ]
        created = {}

        def submit(values):
            limit = values["answer_limit"]
            if limit is not None:
                try:
                    limit = int(limit)
                except ValueError:
                    raise ValidationError("The timeout must be a whole number of seconds.")
            if not values["patient_id"]:
                raise ValidationError("A patient is required.")
            created["interview"] = create_interview(
                values["patient_id"], values["bank_id"], values["give_feedback"], limit
            )

        FormDialog(self, "New interview", fields, {"give_feedback": False}, submit)
        interview = created.get("interview")
        if interview:
            self.refresh()
            self.list.select(interview.id)
            if messagebox.askyesno("Interviews", "Interview created. Start it now?", parent=self):
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
