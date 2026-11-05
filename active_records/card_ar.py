import db
from active_records.ar import ActiveRecord, ValidationError, clean_text

QR_PREFIX = "CARD1:"


class CardActiveRecord(ActiveRecord):
    table = "Card"
    columns = {"name": "Name"}
    order_by = '"Name" COLLATE NOCASE'

    def validate(self):
        self.name = clean_text(self.name)
        if not self.name:
            raise ValidationError("The card name is required.")

    def before_delete(self):
        used = db.execute(
            'SELECT 1 FROM QuestionCandidateAnswer WHERE "CardId" = ? LIMIT 1', (self.id,)
        ).fetchone()
        if used:
            raise ValidationError(
                "This card is linked to candidate answers. Remove those answers before deleting the card."
            )

    def qr_payload(self):
        return f"{QR_PREFIX}{self.id}"

    @staticmethod
    def parse_qr_payload(text):
        """Return the card id encoded in a QR text, or None if it is not one of our cards."""
        if not text or not text.startswith(QR_PREFIX):
            return None
        card_id = text[len(QR_PREFIX):].strip()
        return card_id or None
