from datetime import date

import db
from active_records.ar import ActiveRecord, ValidationError, clean_text


class PatientActiveRecord(ActiveRecord):
    table = "Patient"
    columns = {"name": "Name", "description": "Description", "birth_date": "BirthDate"}
    order_by = '"Name" COLLATE NOCASE'

    def validate(self):
        self.name = clean_text(self.name)
        self.description = clean_text(self.description)
        self.birth_date = clean_text(self.birth_date)
        if not self.name:
            raise ValidationError("The patient name is required.")
        if self.birth_date:
            try:
                parsed = date.fromisoformat(self.birth_date)
            except ValueError:
                raise ValidationError("Birth date must have the format YYYY-MM-DD.")
            if parsed > date.today():
                raise ValidationError("Birth date cannot be in the future.")
            self.birth_date = parsed.isoformat()

    def before_delete(self):
        used = db.execute('SELECT 1 FROM Interview WHERE "PatientId" = ? LIMIT 1', (self.id,)).fetchone()
        if used:
            raise ValidationError("This patient has interviews. Delete them before deleting the patient.")

    def age_at(self, moment):
        """Age in whole years at the given date/datetime, or None if unknown."""
        if not self.birth_date or moment is None:
            return None
        born = date.fromisoformat(self.birth_date)
        day = moment.date() if hasattr(moment, "date") else moment
        return day.year - born.year - ((day.month, day.day) < (born.month, born.day))
