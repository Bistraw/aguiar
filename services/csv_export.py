"""Interview results export (one CSV per interview)."""

import csv
import re

import db
from active_records import PatientActiveRecord

COLUMNS = [
    "PatientName",
    "PatientAge",
    "BankName",
    "InterviewStart",
    "Position",
    "QuestionText",
    "Outcome",
    "CardName",
    "IsCorrect",
    "ShownAt",
    "AnsweredAt",
    "ResponseSeconds",
]


def _empty(value):
    return "" if value is None else value


def export_interview_csv(interview_id, path):
    rows = db.execute(
        'SELECT p."Name" AS PatientName, p."BirthDate", b."Name" AS BankName, i."Start", '
        'iq."Position", iq."QuestionText", a."Outcome", a."CardName", a."IsCorrect", a."ShownAt", a."When" '
        "FROM InterviewQuestion iq "
        'JOIN Interview i ON i."Id" = iq."InterviewId" '
        'JOIN Patient p ON p."Id" = i."PatientId" '
        'JOIN QuestionBank b ON b."Id" = i."QuestionBankId" '
        'LEFT JOIN InterviewQuestionAnswer a ON a."InterviewQuestionId" = iq."Id" '
        'WHERE iq."InterviewId" = ? ORDER BY iq."Position"',
        (interview_id,),
    ).fetchall()

    # UTF-8 with BOM so Excel shows accents correctly.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for r in rows:
            patient = PatientActiveRecord(birth_date=r["BirthDate"])
            age = patient.age_at(db.parse_iso(r["Start"]))
            shown, answered = db.parse_iso(r["ShownAt"]), db.parse_iso(r["When"])
            seconds = f"{(answered - shown).total_seconds():.1f}" if shown and answered else ""
            writer.writerow([
                r["PatientName"],
                _empty(age),
                r["BankName"],
                _empty(r["Start"]),
                r["Position"],
                _empty(r["QuestionText"]),
                _empty(r["Outcome"]),
                _empty(r["CardName"]),
                _empty(r["IsCorrect"]),
                _empty(r["ShownAt"]),
                _empty(r["When"]),
                seconds,
            ])
    return len(rows)


def suggested_file_name(patient_name, start_iso):
    safe = re.sub(r"[^\w\-]+", "_", patient_name or "patient").strip("_")
    day = (start_iso or "")[:10] or "not_started"
    return f"interview_{safe}_{day}.csv"
