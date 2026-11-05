import db
from active_records.ar import ActiveRecord, ValidationError, clean_text
from active_records.card_ar import CardActiveRecord


class QuestionCandidateAnswerActiveRecord(ActiveRecord):
    table = "QuestionCandidateAnswer"
    columns = {
        "question_id": "QuestionId",
        "card_id": "CardId",
        "is_correct": "IsCorrect",
        "feedback_text": "FeedbackText",
    }
    defaults = {"is_correct": 0}

    def validate(self):
        self.feedback_text = clean_text(self.feedback_text)
        self.is_correct = 1 if self.is_correct else 0
        if not self.question_id:
            raise ValidationError("The answer must belong to a question.")
        if not self.card_id:
            raise ValidationError("A card is required.")
        duplicate = db.execute(
            'SELECT 1 FROM QuestionCandidateAnswer WHERE "QuestionId" = ? AND "CardId" = ? AND "Id" IS NOT ?',
            (self.question_id, self.card_id, self.id),
        ).fetchone()
        if duplicate:
            raise ValidationError("This card is already an answer of this question.")

    def card(self):
        return CardActiveRecord.get(self.card_id)

    @classmethod
    def find_by_question_and_card(cls, question_id, card_id):
        found = cls.find('"QuestionId" = ? AND "CardId" = ?', (question_id, card_id))
        return found[0] if found else None
