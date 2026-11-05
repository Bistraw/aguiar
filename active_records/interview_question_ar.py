from active_records.ar import ActiveRecord


class InterviewQuestionActiveRecord(ActiveRecord):
    table = "InterviewQuestion"
    columns = {
        "interview_id": "InterviewId",
        "question_id": "QuestionId",
        "question_text": "QuestionText",
        "position": "Position",
    }
    order_by = '"Position"'
