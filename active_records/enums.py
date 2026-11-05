class InterviewStatus:
    CREATED = "Created"
    IN_PROGRESS = "InProgress"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    ABORTED = "Aborted"

    OPEN = (CREATED, IN_PROGRESS, PAUSED)
    FINISHED = (COMPLETED, ABORTED)


class Outcome:
    ANSWERED = "Answered"
    SKIPPED = "Skipped"
    TIMED_OUT = "TimedOut"
