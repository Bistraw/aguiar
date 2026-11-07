"""Interview creation, listing and the runtime flow (no UI)."""

import random

import db
from active_records import (
    CardActiveRecord,
    InterviewActiveRecord,
    InterviewQuestionActiveRecord,
    InterviewQuestionAnswerActiveRecord,
    InterviewStatus,
    Outcome,
    QuestionActiveRecord,
    QuestionBankActiveRecord,
    QuestionCandidateAnswerActiveRecord,
    ValidationError,
)


def create_interview(patient_id, question_bank_id, give_feedback=False, answer_limit=None):
    """Create an interview and fix its shuffled question order (with text snapshots)."""
    bank = QuestionBankActiveRecord.get(question_bank_id)
    if bank is None:
        raise ValidationError("A question bank is required.")
    questions = bank.questions()
    if not questions:
        raise ValidationError("The selected bank has no questions.")
    if any(not q.candidate_answers() for q in questions):
        raise ValidationError("Every question of the bank needs at least one candidate answer.")

    order = list(questions)
    random.shuffle(order)
    with db.transaction():
        interview = InterviewActiveRecord(
            patient_id=patient_id,
            question_bank_id=question_bank_id,
            give_feedback=give_feedback,
            answer_limit=answer_limit,
        ).save()
        for position, question in enumerate(order, start=1):
            InterviewQuestionActiveRecord(
                interview_id=interview.id,
                question_id=question.id,
                question_text=question.text,
                position=position,
            ).save()
    return interview


def list_interviews():
    """Rows for the interviews list."""
    return db.execute(
        'SELECT i."Id", p."Name" AS PatientName, b."Name" AS BankName, i."Status", i."Start", i."End", '
        '(SELECT COUNT(*) FROM InterviewQuestionAnswer a WHERE a."InterviewId" = i."Id") AS Answered, '
        '(SELECT COUNT(*) FROM InterviewQuestion q WHERE q."InterviewId" = i."Id") AS Total '
        'FROM Interview i '
        'JOIN Patient p ON p."Id" = i."PatientId" '
        'JOIN QuestionBank b ON b."Id" = i."QuestionBankId" '
        "ORDER BY i.rowid DESC"
    ).fetchall()


class InterviewSession:
    """Runtime state of an interview being presented."""

    def __init__(self, interview):
        self.interview = interview
        self.total = interview.question_count()
        self.current = None  # InterviewQuestionActiveRecord being shown
        self.shown_at = None

    def start(self):
        if self.interview.status in InterviewStatus.FINISHED:
            raise ValidationError("This interview is already finished.")
        if self.interview.start is None:
            self.interview.start = db.now_iso()
        self.interview.status = InterviewStatus.IN_PROGRESS
        self.interview.save()

    def next_question(self):
        """Advance to the next pending question; returns it (or None when all are done)."""
        self.current = self.interview.next_pending_question()
        self.shown_at = db.now_iso() if self.current else None
        return self.current

    def current_question(self):
        """The live Question record; None if it was deleted (the snapshot text remains on self.current)."""
        return QuestionActiveRecord.get(self.current.question_id) if self.current else None

    def try_answer(self, card_id):
        """Register the card as answer if it is a candidate of the current question. Returns the candidate or None."""
        if self.current is None or self.current.question_id is None:
            return None
        candidate = QuestionCandidateAnswerActiveRecord.find_by_question_and_card(self.current.question_id, card_id)
        if candidate is None:
            return None
        card = CardActiveRecord.get(card_id)
        self._record(Outcome.ANSWERED, candidate, card)
        return candidate

    def skip(self):
        self._record(Outcome.SKIPPED)

    def time_out(self):
        self._record(Outcome.TIMED_OUT)

    def _record(self, outcome, candidate=None, card=None):
        if self.current is None:
            return
        InterviewQuestionAnswerActiveRecord(
            interview_id=self.interview.id,
            interview_question_id=self.current.id,
            question_candidate_answer_id=candidate.id if candidate else None,
            card_id=card.id if card else None,
            outcome=outcome,
            card_name=card.name if card else None,
            is_correct=(1 if candidate.is_correct else 0) if candidate else None,
            shown_at=self.shown_at,
            when=db.now_iso(),
        ).save()
        self.current = None
        self.shown_at = None

    def outcome_counts(self):
        """Number of recorded answers per Outcome."""
        rows = db.execute(
            'SELECT "Outcome", COUNT(*) FROM InterviewQuestionAnswer WHERE "InterviewId" = ? GROUP BY "Outcome"',
            (self.interview.id,),
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def pause(self):
        self._finish_with(InterviewStatus.PAUSED, set_end=False)

    def abort(self):
        self._finish_with(InterviewStatus.ABORTED, set_end=True)

    def complete(self):
        self._finish_with(InterviewStatus.COMPLETED, set_end=True)

    def _finish_with(self, status, set_end):
        self.interview.status = status
        if set_end:
            self.interview.end = db.now_iso()
        self.interview.save()
        self.current = None
