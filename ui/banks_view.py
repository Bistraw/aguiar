import io
import sqlite3
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from active_records import (
    CardActiveRecord,
    QuestionActiveRecord,
    QuestionBankActiveRecord,
    QuestionCandidateAnswerActiveRecord,
    ValidationError,
)
from active_records.question_ar import validate_image
from ui import theme
from ui.common import Action, Dialog, FormDialog, ListPanel, confirm, make_button, make_text, run_action, short
from ui.icons import icon
from ui.theme import px

STATUS_READY = ("checkmark", theme.SUCCESS)
STATUS_INCOMPLETE = ("warning", theme.WARNING)


def _crud_actions(new, edit, delete):
    return [
        Action("New", new, "plus", "primary", needs_selection=False, key="new"),
        Action("Edit", edit, "wrench"),
        Action("Delete", delete, "trashcan", "danger"),
    ]


class BanksView(ttk.Frame):
    """Question banks, their questions and the candidate answers of the selected question."""

    def __init__(self, parent):
        super().__init__(parent)
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self.banks = ListPanel(
            paned, "Question banks", [("Name", 130), ("Questions", 75, False)],
            _crud_actions(self.new_bank, self.edit_bank, self.delete_bank),
            on_select=self.refresh_questions, on_activate=self.edit_bank, on_delete=self.delete_bank,
            status_column=True, auto_select=True,
        )
        self.questions = ListPanel(
            paned, "Questions", [("Text", 210), ("Image", 55, False), ("Answers", 65, False)],
            _crud_actions(self.new_question, self.edit_question, self.delete_question),
            on_select=self.refresh_answers, on_activate=self.edit_question, on_delete=self.delete_question,
            status_column=True, auto_select=True,
        )
        self.answers = ListPanel(
            paned, "Candidate answers", [("Card", 110), ("Expected", 70, False), ("Feedback", 120)],
            _crud_actions(self.new_answer, self.edit_answer, self.delete_answer),
            on_activate=self.edit_answer, on_delete=self.delete_answer,
        )
        self.banks.set_empty("question", "No question banks yet", "A bank groups the questions of an interview.",
                             ("New bank", self.new_bank, "plus"))
        paned.add(self.banks, weight=1)
        paned.add(self.questions, weight=1)
        paned.add(self.answers, weight=1)
        self._paned_width = None
        paned.bind("<Configure>", self._on_paned_resized)

    def _on_paned_resized(self, event):
        """Equal panels whenever the window width changes, so no toolbar gets clipped. Dragging a sash still works."""
        if event.width != self._paned_width:
            self._paned_width = event.width
            event.widget.sashpos(0, event.width // 3)
            event.widget.sashpos(1, event.width * 2 // 3)

    # --- refresh ---

    def refresh(self):
        self.banks.set_rows(self._bank_row(b) for b in QuestionBankActiveRecord.all())
        self.refresh_questions()

    @staticmethod
    def _bank_row(bank):
        questions = bank.questions()
        ready = questions and all(q.candidate_answers() for q in questions)
        return bank.id, [bank.name, len(questions)], STATUS_READY if ready else STATUS_INCOMPLETE

    def refresh_questions(self):
        bank = QuestionBankActiveRecord.get(self.banks.selected_id())
        self.questions.set_enabled("new", bank is not None)
        if bank:
            self.questions.set_subtitle(short(bank.description, 90) or bank.name)
            self.questions.set_empty("question", "No questions in this bank", "Add at least one to use it in an interview.")
        else:
            self.questions.set_subtitle("")
            self.questions.set_empty("question", "No bank selected", "Select a question bank to see its questions.")
        rows = []
        if bank:
            for q in bank.questions():
                count = len(q.candidate_answers())
                rows.append((q.id, [short(q.text) or "(image only)", "Yes" if q.image else "", count],
                             None if count else STATUS_INCOMPLETE))
        self.questions.set_rows(rows)
        self.refresh_answers()

    def refresh_answers(self):
        question = QuestionActiveRecord.get(self.questions.selected_id())
        self.answers.set_enabled("new", question is not None)
        if question:
            self.answers.set_subtitle(short(question.text, 90) or "(image only)")
            self.answers.set_empty("warning", "No answers yet",
                                   "Add the cards that can answer this question. It is required to start an interview.")
        else:
            self.answers.set_subtitle("")
            self.answers.set_empty("menuGrid", "No question selected", "Select a question to see its answers.")
        rows = []
        if question:
            for a in question.candidate_answers():
                card = a.card()
                rows.append((a.id, [card.name if card else "?", "Yes" if a.is_correct else "", short(a.feedback_text, 40)]))
        self.answers.set_rows(rows)

    # --- banks ---

    def _bank_form(self, title, bank):
        fields = [
            {"key": "name", "label": "Name", "required": True},
            {"key": "description", "label": "Description", "kind": "text", "height": 4},
        ]

        def submit(values):
            bank.name, bank.description = values["name"], values["description"]
            bank.save()

        if FormDialog(self, title, fields, {"name": bank.name, "description": bank.description}, submit).result:
            self.refresh()
            self.banks.select(bank.id)

    def _selected_bank(self):
        bank = QuestionBankActiveRecord.get(self.banks.selected_id())
        if bank is None:
            messagebox.showinfo("Question banks", "Select a question bank first.", parent=self)
        return bank

    def new_bank(self):
        self._bank_form("New question bank", QuestionBankActiveRecord())

    def edit_bank(self):
        bank = self._selected_bank()
        if bank:
            self._bank_form("Edit question bank", bank)

    def delete_bank(self):
        bank = self._selected_bank()
        if bank and confirm(self, f"Delete bank '{bank.name}' with all its questions?"):
            if run_action(self, bank.delete):
                self.refresh()

    # --- questions ---

    def _selected_question(self):
        question = QuestionActiveRecord.get(self.questions.selected_id())
        if question is None:
            messagebox.showinfo("Questions", "Select a question first.", parent=self)
        return question

    def _question_form(self, title, question):
        dialog = QuestionDialog(self, title, question)
        if dialog.saved:
            self.refresh()
            self.questions.select(question.id)

    def new_question(self):
        bank = self._selected_bank()
        if bank:
            self._question_form("New question", QuestionActiveRecord(question_bank_id=bank.id))

    def edit_question(self):
        question = self._selected_question()
        if question:
            self._question_form("Edit question", question)

    def delete_question(self):
        question = self._selected_question()
        if question and confirm(self, "Delete the selected question and its candidate answers?"):
            if run_action(self, question.delete):
                self.refresh()

    # --- candidate answers ---

    def _selected_answer(self):
        answer = QuestionCandidateAnswerActiveRecord.get(self.answers.selected_id())
        if answer is None:
            messagebox.showinfo("Candidate answers", "Select a candidate answer first.", parent=self)
        return answer

    def _answer_form(self, title, answer):
        cards = CardActiveRecord.all()
        if not cards:
            messagebox.showinfo("Candidate answers", "Create cards first in the Cards page.", parent=self)
            return
        # A card maps to at most one answer per question, so don't offer the ones already taken.
        question = QuestionActiveRecord.get(answer.question_id)
        taken = {a.card_id for a in question.candidate_answers()} - {answer.card_id}
        cards = [c for c in cards if c.id not in taken]
        if not cards:
            messagebox.showinfo("Candidate answers", "All cards are already answers of this question.", parent=self)
            return
        fields = [
            {"key": "card_id", "label": "Card", "kind": "combo", "required": True,
             "options": [(c.id, c.name) for c in cards]},
            {"key": "is_correct", "label": "Expected answer", "kind": "check",
             "hint": "Mark this card as an expected answer"},
            {"key": "feedback_text", "label": "Feedback text", "kind": "text", "height": 3,
             "hint": "Optional. Shown only in interviews with feedback enabled."},
        ]
        initial = {"card_id": answer.card_id, "is_correct": answer.is_correct, "feedback_text": answer.feedback_text}

        def submit(values):
            answer.card_id = values["card_id"]
            answer.is_correct = values["is_correct"]
            answer.feedback_text = values["feedback_text"]
            answer.save()

        if FormDialog(self, title, fields, initial, submit).result is not None:
            self.refresh()
            self.answers.select(answer.id)

    def new_answer(self):
        question = self._selected_question()
        if question:
            self._answer_form("New candidate answer", QuestionCandidateAnswerActiveRecord(question_id=question.id))

    def edit_answer(self):
        answer = self._selected_answer()
        if answer:
            self._answer_form("Edit candidate answer", answer)

    def delete_answer(self):
        answer = self._selected_answer()
        if answer and confirm(self, "Delete the selected candidate answer?"):
            if run_action(self, answer.delete):
                self.refresh()


class QuestionDialog(Dialog):
    PREVIEW_SIZE = (320, 200)

    def __init__(self, parent, title, question):
        super().__init__(parent, title)
        self.question = question
        self.image_bytes = question.image
        self.saved = False
        self._photo = None

        ttk.Label(self.body, text="Text", style="SurfaceBold.TLabel").pack(anchor="w", pady=(0, px(3)))
        self.text = make_text(self.body, height=5, width=55)
        self.text.pack(fill="x")
        if question.text:
            self.text.insert("1.0", question.text)

        ttk.Label(self.body, text="Image", style="SurfaceBold.TLabel").pack(anchor="w", pady=(px(12), px(3)))
        self.preview = ttk.Label(self.body, style="SurfaceMuted.TLabel", compound="left")
        self.preview.pack(anchor="w")
        image_buttons = ttk.Frame(self.body, style="Surface.TFrame")
        image_buttons.pack(anchor="w", pady=(px(6), 0))
        make_button(image_buttons, "Load image…", self._load_image, "import").pack(side="left", padx=(0, px(6)))
        self.remove_button = make_button(image_buttons, "Remove", self._remove_image, "trashcan", "danger")
        self.remove_button.pack(side="left")
        ttk.Label(self.body, text="PNG or JPG, up to 5 MB. A question needs a text, an image or both.",
                  style="SurfaceSmall.TLabel").pack(anchor="w", pady=(px(6), 0))

        buttons = ttk.Frame(self.body, style="Surface.TFrame")
        buttons.pack(fill="x", pady=(px(16), 0))
        make_button(buttons, "Cancel", self.destroy).pack(side="right")
        make_button(buttons, "Save", self._ok, kind="primary").pack(side="right", padx=(0, px(6)))
        self.bind("<Escape>", lambda e: self.destroy())

        self._render_preview()
        self.present(self.text)

    def _render_preview(self):
        if not self.image_bytes:
            self._photo = None
            self.preview.configure(image=icon("target", 20, theme.DISABLED), text="  No image")
            self.remove_button.state(["disabled"])
            return
        with Image.open(io.BytesIO(self.image_bytes)) as img:
            img = img.copy()
        img.thumbnail((px(self.PREVIEW_SIZE[0]), px(self.PREVIEW_SIZE[1])))
        self._photo = ImageTk.PhotoImage(img)
        self.preview.configure(image=self._photo, text="")
        self.remove_button.state(["!disabled"])

    def _load_image(self):
        path = filedialog.askopenfilename(
            parent=self, title="Load image", filetypes=[("Images", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if not path:
            return
        with open(path, "rb") as f:
            data = f.read()
        try:
            validate_image(data)
        except ValidationError as exc:
            self.show_failure(exc)
            return
        self.image_bytes = data
        self._render_preview()

    def _remove_image(self):
        self.image_bytes = None
        self._render_preview()

    def _ok(self):
        self.question.text = self.text.get("1.0", "end")
        self.question.image = self.image_bytes
        try:
            self.question.save()
        except (ValidationError, sqlite3.Error) as exc:
            self.show_failure(exc)
            return
        self.saved = True
        self.destroy()
