import io

from PIL import Image

import db
from active_records.ar import ActiveRecord, ValidationError, clean_text
from active_records.enums import InterviewStatus
from active_records.question_candidate_answer_ar import QuestionCandidateAnswerActiveRecord

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = ("PNG", "JPEG")


class QuestionActiveRecord(ActiveRecord):
    table = "Question"
    columns = {"question_bank_id": "QuestionBankId", "text": "Text", "image": "Image"}

    def validate(self):
        self.text = clean_text(self.text)
        if not self.question_bank_id:
            raise ValidationError("The question must belong to a bank.")
        if self.text is None and self.image is None:
            raise ValidationError("A question needs a text, an image or both.")
        if self.image is not None:
            validate_image(self.image)

    def before_delete(self):
        placeholders = ", ".join("?" * len(InterviewStatus.OPEN))
        used = db.execute(
            f'SELECT 1 FROM InterviewQuestion iq JOIN Interview i ON i."Id" = iq."InterviewId" '
            f'WHERE iq."QuestionId" = ? AND i."Status" IN ({placeholders}) LIMIT 1',
            (self.id, *InterviewStatus.OPEN),
        ).fetchone()
        if used:
            raise ValidationError(
                "This question is part of an interview that is not finished and cannot be deleted."
            )

    def candidate_answers(self):
        return QuestionCandidateAnswerActiveRecord.find('"QuestionId" = ?', (self.id,))


def validate_image(data):
    if len(data) > MAX_IMAGE_BYTES:
        raise ValidationError("The image is larger than 5 MB.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
    except Exception:
        raise ValidationError("The image file could not be read.")
    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Only PNG and JPG images are allowed.")
