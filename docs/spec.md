# What

This software is an aid to psychologist when performing evaluation interviews, its main workflow allows to present a list of questions to the screen and the pacient to answer them.

### Entitites

| Entity                  | Purpose                                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------------------------- |
| QuestionBank            | Set of questions used in interviews.                                                                     |
| Question                | Question (text and/or image) belonging to one bank.                                                      |
| QuestionCandidateAnswer | Possible answer to a question; optionally linked to a Card.                                              |
| Card                    | Physical card. `ExternalId` = decoded QR content.                                                        |
| Patient                 | Patient data only.                                                                                       |
| Interview               | Session for one patient using one bank.                                                                  |
| InterviewQuestionAnswer | Answer history: question, selected answer, card used, timestamp. Independent of bank/card configuration. |

### The interview flow

0. Prepare question Bank, Question, QuestionCandidateAnswer and Card  records
1. Create an Interview (Assign Patient and a QuestionBank).
2. Present question i to the patient
3. Patient inserts card and answer is saved 
4. Repeat from step 2 until all questions are answered or the interview is stoped
5. Present results

### 

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
        Boolean HasText
        String Text
        Boolean HasImage
        BLOB Image
    }
    QuestionCandidateAnswer {
        GUID Id PK
        GUID QuestionId FK
        GUID CardId FK
        Boolean IsCorrect
        String FeedbackText
    }
    Card {
        GUID Id PK
        String ExternalId
        String Name
    }
    Patient {
        GUID Id PK
        String Name
        String Description
        Integer Age
    }
    Interview {
        GUID Id PK
        GUID QuestionBankId FK
        GUID PatientId FK
        DateTime Start
        DateTime End
        Boolean GiveFeedback
        Integer AnswerLimit
    }
    InterviewQuestionAnswer {
        GUID Id PK
        GUID InterviewId FK
        GUID QuestionId FK
        GUID QuestionCandidateAnswerId FK
        GUID CardId FK
        DateTime When
    }

    QuestionBank ||--|{ Question : contains
    QuestionBank ||--o{ Interview : "used in"
    Question ||--o{ QuestionCandidateAnswer : has
    Question ||--o{ InterviewQuestionAnswer : "answered in"
    QuestionCandidateAnswer |o--o| Card : "linked to"
    QuestionCandidateAnswer |o--o{ InterviewQuestionAnswer : "selected in"
    Card ||--o{ InterviewQuestionAnswer : "used in"
    Patient ||--o{ Interview : "takes part in"
    Interview ||--o{ InterviewQuestionAnswer : records
```

### Indexes

| Table                   | Field                   | Purpose                                  |
| ----------------------- | ----------------------- | ---------------------------------------- |
| Card                    | ExternalId (**unique**) | Identify the inserted card.              |
| Question                | QuestionBankId          | Questions of a bank.                     |
| QuestionCandidateAnswer | QuestionId              | Answers of a question.                   |
| QuestionCandidateAnswer | CardId                  | Answer matching a card.                  |
| Interview               | QuestionBankId          | Bank used by an interview.               |
| Interview               | PatientId               | Interviews of a patient.                 |
| InterviewQuestionAnswer | InterviewId             | All answers of an interview (most used). |
| InterviewQuestionAnswer | QuestionId              | Answer for a question.                   |
| InterviewQuestionAnswer | CardId                  | Card used in an answer.                  |

