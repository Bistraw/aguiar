from active_records.ar import ActiveRecord, ValidationError
from active_records.enums import Outcome


class InterviewQuestionAnswerActiveRecord(ActiveRecord):
    table = "InterviewQuestionAnswer"
    columns = {
        "interview_id": "InterviewId",
        "interview_question_id": "InterviewQuestionId",
        "question_candidate_answer_id": "QuestionCandidateAnswerId",
        "card_id": "CardId",
        "outcome": "Outcome",
        "card_name": "CardName",
        "is_correct": "IsCorrect",
        "shown_at": "ShownAt",
        "when": "When",
    }

    def validate(self):
        if self.outcome not in (Outcome.ANSWERED, Outcome.SKIPPED, Outcome.TIMED_OUT):
            raise ValidationError(f"Invalid outcome: {self.outcome}")
        if self.outcome == Outcome.ANSWERED and not self.card_id:
            raise ValidationError("An answered question needs a card.")
