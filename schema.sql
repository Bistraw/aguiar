-- Database creation script. Safe to run on every startup.

CREATE TABLE IF NOT EXISTS QuestionBank (
    "Id"          TEXT PRIMARY KEY,
    "Name"        TEXT NOT NULL,
    "Description" TEXT
);

CREATE TABLE IF NOT EXISTS Question (
    "Id"             TEXT PRIMARY KEY,
    "QuestionBankId" TEXT NOT NULL REFERENCES QuestionBank("Id") ON DELETE CASCADE,
    "Text"           TEXT,
    "Image"          BLOB,
    CHECK ("Text" IS NOT NULL OR "Image" IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS Card (
    "Id"   TEXT PRIMARY KEY,
    "Name" TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS QuestionCandidateAnswer (
    "Id"           TEXT PRIMARY KEY,
    "QuestionId"   TEXT NOT NULL REFERENCES Question("Id") ON DELETE CASCADE,
    "CardId"       TEXT NOT NULL REFERENCES Card("Id") ON DELETE RESTRICT,
    "IsCorrect"    INTEGER NOT NULL DEFAULT 0,
    "FeedbackText" TEXT
);

CREATE TABLE IF NOT EXISTS Patient (
    "Id"          TEXT PRIMARY KEY,
    "Name"        TEXT NOT NULL,
    "Description" TEXT,
    "BirthDate"   TEXT
);

CREATE TABLE IF NOT EXISTS Interview (
    "Id"             TEXT PRIMARY KEY,
    "QuestionBankId" TEXT NOT NULL REFERENCES QuestionBank("Id") ON DELETE RESTRICT,
    "PatientId"      TEXT NOT NULL REFERENCES Patient("Id") ON DELETE RESTRICT,
    "Start"          TEXT,
    "End"            TEXT,
    "Status"         TEXT NOT NULL DEFAULT 'Created'
                     CHECK ("Status" IN ('Created', 'InProgress', 'Paused', 'Completed', 'Aborted')),
    "GiveFeedback"   INTEGER NOT NULL DEFAULT 0,
    "AnswerLimit"    INTEGER CHECK ("AnswerLimit" IS NULL OR "AnswerLimit" > 0)
);

CREATE TABLE IF NOT EXISTS InterviewQuestion (
    "Id"           TEXT PRIMARY KEY,
    "InterviewId"  TEXT NOT NULL REFERENCES Interview("Id") ON DELETE CASCADE,
    "QuestionId"   TEXT REFERENCES Question("Id") ON DELETE SET NULL,
    "QuestionText" TEXT,
    "Position"     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS InterviewQuestionAnswer (
    "Id"                        TEXT PRIMARY KEY,
    "InterviewId"               TEXT NOT NULL REFERENCES Interview("Id") ON DELETE CASCADE,
    "InterviewQuestionId"       TEXT NOT NULL REFERENCES InterviewQuestion("Id") ON DELETE CASCADE,
    "QuestionCandidateAnswerId" TEXT REFERENCES QuestionCandidateAnswer("Id") ON DELETE SET NULL,
    "CardId"                    TEXT REFERENCES Card("Id") ON DELETE SET NULL,
    "Outcome"                   TEXT NOT NULL CHECK ("Outcome" IN ('Answered', 'Skipped', 'TimedOut')),
    "CardName"                  TEXT,
    "IsCorrect"                 INTEGER,
    "ShownAt"                   TEXT NOT NULL,
    "When"                      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Setting (
    "Key"   TEXT PRIMARY KEY,
    "Value" TEXT
);

CREATE INDEX IF NOT EXISTS IX_Question_QuestionBankId ON Question("QuestionBankId");
CREATE INDEX IF NOT EXISTS IX_QuestionCandidateAnswer_QuestionId ON QuestionCandidateAnswer("QuestionId");
CREATE INDEX IF NOT EXISTS IX_QuestionCandidateAnswer_CardId ON QuestionCandidateAnswer("CardId");
CREATE UNIQUE INDEX IF NOT EXISTS UX_QuestionCandidateAnswer_QuestionId_CardId ON QuestionCandidateAnswer("QuestionId", "CardId");
CREATE INDEX IF NOT EXISTS IX_Interview_QuestionBankId ON Interview("QuestionBankId");
CREATE INDEX IF NOT EXISTS IX_Interview_PatientId ON Interview("PatientId");
CREATE UNIQUE INDEX IF NOT EXISTS UX_InterviewQuestion_InterviewId_Position ON InterviewQuestion("InterviewId", "Position");
CREATE INDEX IF NOT EXISTS IX_InterviewQuestion_QuestionId ON InterviewQuestion("QuestionId");
CREATE INDEX IF NOT EXISTS IX_InterviewQuestionAnswer_InterviewId ON InterviewQuestionAnswer("InterviewId");
CREATE UNIQUE INDEX IF NOT EXISTS UX_InterviewQuestionAnswer_InterviewQuestionId ON InterviewQuestionAnswer("InterviewQuestionId");
CREATE INDEX IF NOT EXISTS IX_InterviewQuestionAnswer_CardId ON InterviewQuestionAnswer("CardId");
