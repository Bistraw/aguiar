import io
import tkinter as tk
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
from ui.common import FONT, FormDialog, ListPanel, confirm, run_action, short, show_error


class BanksView(ttk.Frame):
    """Question banks, their questions and the candidate answers of the selected question."""

    def __init__(self, parent):
        super().__init__(parent, padding=8)
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self.banks = ListPanel(
            paned, "Question banks", [("Name", 150), ("Description", 170)],
            [("New", self.new_bank), ("Edit", self.edit_bank), ("Delete", self.delete_bank)],
            on_select=self.refresh_questions, on_activate=self.edit_bank,
        )
        self.questions = ListPanel(
            paned, "Questions", [("Text", 260), ("Image", 55), ("Answers", 65)],
            [("New", self.new_question), ("Edit", self.edit_question), ("Delete", self.delete_question)],
            on_select=self.refresh_answers, on_activate=self.edit_question,
        )
        self.answers = ListPanel(
            paned, "Candidate answers", [("Card", 130), ("Expected", 70), ("Feedback", 180)],
            [("New", self.new_answer), ("Edit", self.edit_answer), ("Delete", self.delete_answer)],
            on_activate=self.edit_answer,
        )
        paned.add(self.banks, weight=1)
        paned.add(self.questions, weight=2)
        paned.add(self.answers, weight=2)

    # --- refresh ---

    def refresh(self):
        self.banks.set_rows((b.id, [b.name, short(b.description, 40)]) for b in QuestionBankActiveRecord.all())
        self.refresh_questions()

    def refresh_questions(self):
        bank = QuestionBankActiveRecord.get(self.banks.selected_id())
        rows = []
        if bank:
            for q in bank.questions():
                rows.append((q.id, [short(q.text) or "(image only)", "Yes" if q.image else "", len(q.candidate_answers())]))
        self.questions.set_rows(rows)
        self.refresh_answers()

    def refresh_answers(self):
        question = QuestionActiveRecord.get(self.questions.selected_id())
        rows = []
        if question:
            for a in question.candidate_answers():
                card = a.card()
                rows.append((a.id, [card.name if card else "?", "Yes" if a.is_correct else "", short(a.feedback_text, 40)]))
        self.answers.set_rows(rows)

    # --- banks ---

    def _bank_form(self, title, bank):
        fields = [
            {"key": "name", "label": "Name"},
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
            self.refresh_questions()
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
                self.refresh_questions()

    # --- candidate answers ---

    def _selected_answer(self):
        answer = QuestionCandidateAnswerActiveRecord.get(self.answers.selected_id())
        if answer is None:
            messagebox.showinfo("Candidate answers", "Select a candidate answer first.", parent=self)
        return answer

    def _answer_form(self, title, answer):
        cards = CardActiveRecord.all()
        if not cards:
            messagebox.showinfo("Candidate answers", "Create cards first in the Cards tab.", parent=self)
            return
        fields = [
            {"key": "card_id", "label": "Card", "kind": "combo", "options": [(c.id, c.name) for c in cards]},
            {"key": "is_correct", "label": "Expected answer", "kind": "check"},
            {"key": "feedback_text", "label": "Feedback text", "kind": "text", "height": 3},
        ]
        initial = {"card_id": answer.card_id, "is_correct": answer.is_correct, "feedback_text": answer.feedback_text}

        def submit(values):
            answer.card_id = values["card_id"]
            answer.is_correct = values["is_correct"]
            answer.feedback_text = values["feedback_text"]
            answer.save()

        if FormDialog(self, title, fields, initial, submit).result is not None:
            self.refresh_questions()
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
                self.refresh_questions()


class QuestionDialog(tk.Toplevel):
    PREVIEW_SIZE = (320, 220)

    def __init__(self, parent, title, question):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.question = question
        self.image_bytes = question.image
        self.saved = False
        self._photo = None

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Text").grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.text = tk.Text(body, width=55, height=6, wrap="word", font=FONT)
        self.text.grid(row=0, column=1, sticky="we")
        if question.text:
            self.text.insert("1.0", question.text)

        ttk.Label(body, text="Image").grid(row=1, column=0, sticky="nw", padx=(0, 8), pady=(8, 0))
        image_box = ttk.Frame(body)
        image_box.grid(row=1, column=1, sticky="w", pady=(8, 0))
        self.preview = ttk.Label(image_box, text="(no image)", anchor="center")
        self.preview.pack(anchor="w")
        image_buttons = ttk.Frame(image_box)
        image_buttons.pack(anchor="w", pady=(4, 0))
        ttk.Button(image_buttons, text="Load image…", command=self._load_image).pack(side="left", padx=(0, 4))
        ttk.Button(image_buttons, text="Remove image", command=self._remove_image).pack(side="left")
        ttk.Label(body, text="PNG or JPG, up to 5 MB. A question needs a text, an image or both.",
                  foreground="gray").grid(row=2, column=1, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="OK", command=self._ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())

        self._render_preview()
        self.grab_set()
        self.text.focus_set()
        self.wait_window()

    def _render_preview(self):
        if not self.image_bytes:
            self._photo = None
            self.preview.configure(image="", text="(no image)")
            return
        with Image.open(io.BytesIO(self.image_bytes)) as img:
            img = img.copy()
        img.thumbnail(self.PREVIEW_SIZE)
        self._photo = ImageTk.PhotoImage(img)
        self.preview.configure(image=self._photo, text="")

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
            show_error(self, exc)
            return
        self.image_bytes = data
        self._render_preview()

    def _remove_image(self):
        self.image_bytes = None
        self._render_preview()

    def _ok(self):
        self.question.text = self.text.get("1.0", "end")
        self.question.image = self.image_bytes
        if run_action(self, self.question.save):
            self.saved = True
            self.destroy()
