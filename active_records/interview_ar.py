import db
from active_records.ar import ActiveRecord, ValidationError
from active_records.enums import InterviewStatus
from active_records.interview_question_ar import InterviewQuestionActiveRecord
from active_records.patient_ar import PatientActiveRecord
from active_records.question_bank_ar import QuestionBankActiveRecord


class InterviewActiveRecord(ActiveRecord):
    table = "Interview"
    columns = {
        "question_bank_id": "QuestionBankId",
        "patient_id": "PatientId",
        "start": "Start",
        "end": "End",
        "status": "Status",
        "give_feedback": "GiveFeedback",
        "answer_limit": "AnswerLimit",
    }
    defaults = {"status": InterviewStatus.CREATED, "give_feedback": 0}
    order_by = "rowid DESC"

    def validate(self):
        self.give_feedback = 1 if self.give_feedback else 0
        if not self.patient_id:
            raise ValidationError("A patient is required.")
        if not self.question_bank_id:
            raise ValidationError("A question bank is required.")
        if self.answer_limit is not None and (not isinstance(self.answer_limit, int) or self.answer_limit <= 0):
            raise ValidationError("The timeout must be a positive number of seconds.")

    def patient(self):
        return PatientActiveRecord.get(self.patient_id)

    def question_bank(self):
        return QuestionBankActiveRecord.get(self.question_bank_id)

    def interview_questions(self):
        return InterviewQuestionActiveRecord.find('"InterviewId" = ?', (self.id,))

    def question_count(self):
        return db.execute('SELECT COUNT(*) FROM InterviewQuestion WHERE "InterviewId" = ?', (self.id,)).fetchone()[0]

    def next_pending_question(self):
        """First scheduled question (by position) without an answer row."""
        found = InterviewQuestionActiveRecord.find(
            '"InterviewId" = ? AND NOT EXISTS (SELECT 1 FROM InterviewQuestionAnswer a '
            'WHERE a."InterviewQuestionId" = InterviewQuestion."Id")',
            (self.id,),
        )
        return found[0] if found else None
