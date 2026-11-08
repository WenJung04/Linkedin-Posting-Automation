"""Event session state machine. Pure logic, no Telegram or database code.

capturing --/done--> asking --last answer--> ready --draft ok--> drafted
Any active session can be cancelled.
"""

from dataclasses import dataclass, replace

CAPTURING = "capturing"
ASKING = "asking"
READY = "ready"  # answers collected, draft not generated yet (or it failed)
DRAFTED = "drafted"
CANCELLED = "cancelled"

ACTIVE_STATUSES = (CAPTURING, ASKING)
DRAFTABLE_STATUSES = (READY, DRAFTED)

QUESTIONS = [
    ("takeaway", "What's the ONE takeaway you want people to remember?"),
    ("people", "Who did you meet? Names, roles, companies. Or 'skip'."),
    ("next_step", "What will you do next because of this event? Or 'skip'."),
]

SKIP_WORDS = {"skip", "-", "none", "no", "nil", "n/a", "na"}


class SessionError(Exception):
    """An action that is not allowed in the session's current status."""


@dataclass(frozen=True)
class Session:
    event_id: int
    name: str
    status: str = CAPTURING
    question_index: int = 0


def clean_event_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name:
        raise SessionError("Give the event a name, e.g. /event ETH KL Meetup")
    return name[:100]


def can_capture(session: Session) -> bool:
    return session.status == CAPTURING


def finish_capture(session: Session) -> Session:
    if session.status != CAPTURING:
        raise SessionError("This event is not capturing anymore.")
    return replace(session, status=ASKING, question_index=0)


def current_question(session: Session) -> tuple[str, str] | None:
    if session.status != ASKING or session.question_index >= len(QUESTIONS):
        return None
    return QUESTIONS[session.question_index]


def normalize_answer(text: str) -> str | None:
    """Return the cleaned answer, or None if the question was skipped."""
    answer = text.strip()
    if answer.lower().strip(".!") in SKIP_WORDS or not answer:
        return None
    return answer


def record_answer(session: Session) -> Session:
    """Advance past the current question. The caller stores the answer itself."""
    if current_question(session) is None:
        raise SessionError("There is no question waiting for an answer.")
    next_index = session.question_index + 1
    status = READY if next_index >= len(QUESTIONS) else ASKING
    return replace(session, status=status, question_index=next_index)


def mark_drafted(session: Session) -> Session:
    if session.status not in DRAFTABLE_STATUSES:
        raise SessionError("Answer the questions before drafting.")
    return replace(session, status=DRAFTED)


def cancel(session: Session) -> Session:
    if session.status not in ACTIVE_STATUSES:
        raise SessionError("This event is already finished.")
    return replace(session, status=CANCELLED)
