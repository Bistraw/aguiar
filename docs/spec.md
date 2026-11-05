# What

This software is an aid to psychologists when performing evaluation interviews, its main workflow presents a list of questions on the screen for the patient to answer.

### Entities

| Entity                  | Purpose                                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------------------------- |
| QuestionBank            | Set of questions used in interviews.                                                                     |
| Question                | Question (text and/or image) belonging to one bank.                                                      |
| QuestionCandidateAnswer | Possible answer to a question; always linked to a Card.                                                  |
| Card                    | Physical card. Its QR encodes `CARD1:<Card.Id>`.                                                         |
| Patient                 | Patient data only.                                                                                       |
| Interview               | Session for one patient using one bank.                                                                  |
| InterviewQuestion       | Questions of an interview in presented (shuffled) order, with a text snapshot.                          |
| InterviewQuestionAnswer | Answer history: question, selected answer, card used, timestamp. Independent of bank/card configuration. |
| Setting                 | Key/value app settings.                                                                                  |

### The interview flow

0. Prepare question Bank, Question, QuestionCandidateAnswer and Card records
1. Create an Interview (Assign Patient and a QuestionBank). Blocked if the bank has no questions or any question has no candidate answers.
2. Present question i to the patient
3. Patient shows a card to the camera (or the psychologist skips) and the answer is saved
4. Repeat from step 2 until all questions are answered or the interview is stopped
5. Present results

Notes: 

Both the psychologist and the patient will see the same screen, a laptop screen. The next question will be presented if either the psychologist skips the question by clicking a button on the screen or the patient answers by scanning the qr in one of the answer cards.

Psychologist controls are small, discreet buttons at the bottom of the interview screen, also available as keyboard shortcuts: `Space` = skip, `Esc` = pause/stop.

`Esc` (or the pause/stop button) stops the timer and opens a dialog:
- **Continue**: back to the current question; the timer resumes.
- **Pause**: leave the interview to resume later (`Status = Paused`).
- **End interview**: finish it now (`Status = Aborted`); remaining questions stay unanswered.

On resume, the current question is presented again with a new `ShownAt` and the full timeout.

When the timeout expires, the question is recorded as `TimedOut` and the next one is presented. After the last question, an "Interview completed" screen is shown with an "Export CSV" button.

The questions are shown in a random order. This may change in the future but for now that is good enough. The order is generated once when the interview is created and stored in `InterviewQuestion`; resuming continues at the first position without an answer. Questions added to the bank afterwards are not included. A question scheduled in an interview with `Status` Created, InProgress or Paused cannot be deleted.

There are no "wrong answers", that means an answer is registered whether or not it is correct. The intent of this tool is to evaluate, not to teach.

There is a timeout per question, which can be configured in the interview settings (`Interview.AnswerLimit`). When set, a discreet indicator (small progress bar / remaining seconds) is shown near the psychologist controls.

Feedback is off by default. Only when the interview explicitly enables it (`Interview.GiveFeedback`), the selected answer's `FeedbackText` (if any) is shown after answering, and stays until the psychologist clicks to continue. The answer is already saved; while the feedback is shown there is no timer and scans are ignored. The next question's timer starts when it is presented.

Interviews can be stopped and resumed.

### The answer cards and reader

Cards are general purpose answers, mainly emotions, so a simple set of cards (for example happy, sad, angry) could serve as the possible answer set for multiple questions. A question may have one or several expected answers (`IsCorrect`), still we are interested in recording what card was used to answer and whether or not it was the "expected" one.

For the first version, the card reader uses the webcam to scan the QR code in the card. If no camera is available, an error is shown and the interview cannot start; other scanning methods may be added in a future revision. When several cameras exist, the one to use is selected in the app settings (default: first camera). The interview screen shows a small live camera preview so the patient can aim the card. New cards are registered with an autogenerated GUID (`Card.Id`). The QR content is `CARD1:<Card.Id>` (`CARD1` = format prefix and version). On scan: if the prefix doesn't match, or the id is not a candidate answer of the current question, the scan is ignored; otherwise it is registered as the answer. No encryption/signature: a copied card is accepted as the original.

After an answer is registered, scans are ignored until no QR has been detected for ~1 second (the card was removed), to avoid one card answering several questions.

Ignored scans (unknown prefix, unknown card, or card not linked to the current question) are not stored.

The card screen has an "Export QR" action that saves a PNG with the QR and the card `Name` below it, ready to print.

### The results

For this first version, results are returned in a *.csv file, one file per interview.

- Encoding UTF-8 with BOM, comma delimiter, header row.
- One row per `InterviewQuestion`, in presented order (`Position`). Questions not reached (stopped interview) have an empty `Outcome`.
- Interview-level fields are repeated on every row so the file is self-contained.
- Values: `IsCorrect` = 1/0; dates ISO-8601 as stored; `ResponseSeconds` with 1 decimal; NULL = empty cell (e.g. `PatientAge` without `BirthDate`, fields of unanswered questions).

| Column          | Source                                          |
| --------------- | ----------------------------------------------- |
| PatientName     | Patient.Name                                    |
| PatientAge      | computed from Patient.BirthDate at Interview.Start |
| BankName        | QuestionBank.Name                               |
| InterviewStart  | Interview.Start                                 |
| Position        | InterviewQuestion.Position                      |
| QuestionText    | InterviewQuestion.QuestionText (snapshot; filled even if not reached) |
| Outcome         | Answered / Skipped / TimedOut                   |
| CardName        | InterviewQuestionAnswer.CardName (snapshot)     |
| IsCorrect       | InterviewQuestionAnswer.IsCorrect (snapshot)    |
| ShownAt         | InterviewQuestionAnswer.ShownAt                 |
| AnsweredAt      | InterviewQuestionAnswer.When                    |
| ResponseSeconds | When - ShownAt                                  |

### Other must know

- This app should be a desktop app (Windows), distributed as a portable `.exe` built with PyInstaller. `db.sqlite` lives next to the `.exe`.
- v1 screens: management (create/edit) of Question Banks with their Questions and Candidate Answers, Cards (with "Export QR"), Patients; an Interviews list to create, resume and export CSV; Settings; and the Interview screen.
- Language: UI text and CSV headers/values in English.
- Question images: PNG or JPG, max ~5 MB, stored as BLOB, scaled to fit the question area keeping aspect ratio.
- Privacy: v1 has no login and no database encryption. Protecting the machine and its OS account is the user's responsibility.

# How

## Database schema

### ER Diagram

```mermaid
erDiagram
    QuestionBank {
        GUID Id PK
        String Name
        String Description
    }
    Question {
        GUID Id PK
        GUID QuestionBankId FK
        String Text "nullable"
        BLOB Image "nullable; at least one of Text/Image required"
    }
    QuestionCandidateAnswer {
        GUID Id PK
        GUID QuestionId FK
        GUID CardId FK "required"
        Boolean IsCorrect
        String FeedbackText "optional; shown only if Interview.GiveFeedback"
    }
    Card {
        GUID Id PK
        String Name
    }
    Patient {
        GUID Id PK
        String Name
        String Description
        Date BirthDate "age computed when needed"
    }
    Interview {
        GUID Id PK
        GUID QuestionBankId FK
        GUID PatientId FK
        DateTime Start "set when first started; NULL while Created"
        DateTime End "set when Completed or Aborted"
        String Status "Created | InProgress | Paused | Completed | Aborted"
        Boolean GiveFeedback "default false"
        Integer AnswerLimit "per-question timeout in seconds; NULL = no timeout"
    }
    InterviewQuestion {
        GUID Id PK
        GUID InterviewId FK
        GUID QuestionId FK "nullable"
        String QuestionText "snapshot"
        Integer Position "shuffled order, fixed at interview creation"
    }
    InterviewQuestionAnswer {
        GUID Id PK
        GUID InterviewId FK
        GUID InterviewQuestionId FK "unique; one answer per scheduled question"
        GUID QuestionCandidateAnswerId FK "nullable"
        GUID CardId FK "nullable"
        String Outcome "Answered | Skipped | TimedOut"
        String CardName "snapshot; NULL if not answered"
        Boolean IsCorrect "snapshot; NULL if not answered"
        DateTime ShownAt "when the question was presented"
        DateTime When "response time = When - ShownAt"
    }

    Setting {
        String Key PK
        String Value
    }

    QuestionBank ||--|{ Question : contains
    QuestionBank ||--o{ Interview : "used in"
    Question ||--o{ QuestionCandidateAnswer : has
    Card ||--o{ QuestionCandidateAnswer : "linked to"
    QuestionCandidateAnswer |o--o{ InterviewQuestionAnswer : "selected in"
    Card |o--o{ InterviewQuestionAnswer : "used in"
    Patient ||--o{ Interview : "takes part in"
    Interview ||--o{ InterviewQuestionAnswer : records
    Interview ||--|{ InterviewQuestion : "presents in order"
    Question ||--o{ InterviewQuestion : "scheduled in"
    InterviewQuestion ||--o| InterviewQuestionAnswer : "answered by"
```

### Indexes

| Table                   | Field                   | Purpose                                  |
| ----------------------- | ----------------------- | ---------------------------------------- |
| Question                | QuestionBankId          | Questions of a bank.                     |
| QuestionCandidateAnswer | QuestionId              | Answers of a question.                   |
| QuestionCandidateAnswer | CardId                  | Answer matching a card.                  |
| QuestionCandidateAnswer | QuestionId, CardId (**unique**) | A card maps to at most one answer per question. |
| Interview               | QuestionBankId          | Bank used by an interview.               |
| Interview               | PatientId               | Interviews of a patient.                 |
| InterviewQuestion       | InterviewId, Position (**unique**) | Question order of an interview.  |
| InterviewQuestionAnswer | InterviewId             | All answers of an interview (most used). |
| InterviewQuestionAnswer | InterviewQuestionId (**unique**) | Answer of a scheduled question. |
| InterviewQuestionAnswer | CardId                  | Card used in an answer.                  |

Notes:

GUIDs should be stored in a TEXT field.

`QuestionCandidateAnswer.CardId` uses `ON DELETE RESTRICT`: a card linked to candidate answers cannot be deleted until those answers are removed.

`Setting` is a key/value table for app settings (e.g. `CameraIndex`).

Dates and DateTimes are stored as ISO-8601 TEXT in local time, including the UTC offset (e.g. `2026-11-04T10:30:00-06:00`).

`InterviewQuestionAnswer` keeps snapshot columns (`CardName`, `IsCorrect`) copied at save time, so results stay valid if the bank or cards are later edited or deleted. Its FKs to QuestionCandidateAnswer and Card use `ON DELETE SET NULL`.

`InterviewQuestion` keeps the `QuestionText` snapshot copied at interview creation (answers reach it via `InterviewQuestionId`); its FK to Question uses `ON DELETE SET NULL`, so the saved order and the CSV survive question deletion.

## The stack

- use python as the preferred programming language
- use the tkinter library for the UI
- use sqlite as the database
- libraries: `opencv-python` (camera + QR decoding), `Pillow` (images in Tkinter), `qrcode` (QR generation), `pyinstaller` (packaging)

## The architecture

- `active_records/`: one active record class per entity (load/save/delete itself).
- `db.py`: SQLite connection and transaction helper used by the active records (no Unit of Work pattern). Runs `PRAGMA foreign_keys = ON` on every connection.
- `ui/`: Tkinter screens.
- `services/`: interview flow, QR scanner (webcam capture runs in a background thread), CSV export, QR image export.
- `schema.sql`: database creation script.
- `main.py`: entry point.
