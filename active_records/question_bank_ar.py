import db
from active_records.ar import ActiveRecord, ValidationError, clean_text
from active_records.question_ar import QuestionActiveRecord


class QuestionBankActiveRecord(ActiveRecord):
    table = "QuestionBank"
    columns = {"name": "Name", "description": "Description"}
    order_by = '"Name" COLLATE NOCASE'

    def validate(self):
        self.name = clean_text(self.name)
        self.description = clean_text(self.description)
        if not self.name:
            raise ValidationError("The bank name is required.")

    def before_delete(self):
        used = db.execute('SELECT 1 FROM Interview WHERE "QuestionBankId" = ? LIMIT 1', (self.id,)).fetchone()
        if used:
            raise ValidationError("This bank is used by interviews and cannot be deleted.")

    def questions(self):
        return QuestionActiveRecord.find('"QuestionBankId" = ?', (self.id,))
