import pytest

from bot.session import (
    ASKING,
    CANCELLED,
    CAPTURING,
    DRAFTED,
    QUESTIONS,
    READY,
    Session,
    SessionError,
    can_capture,
    cancel,
    clean_event_name,
    current_question,
    finish_capture,
    mark_drafted,
    normalize_answer,
    record_answer,
)


def test_full_flow_reaches_drafted():
    session = Session(1, "ETH KL")
    assert can_capture(session)

    session = finish_capture(session)
    assert session.status == ASKING
    asked = []
    while current_question(session):
        asked.append(current_question(session)[0])
        session = record_answer(session)

    assert asked == [key for key, _ in QUESTIONS]
    assert session.status == READY
    assert mark_drafted(session).status == DRAFTED


def test_redraft_allowed_after_drafted():
    session = Session(1, "x", status=DRAFTED)
    assert mark_drafted(session).status == DRAFTED


def test_cannot_draft_while_capturing():
    with pytest.raises(SessionError):
        mark_drafted(Session(1, "x"))


def test_no_capture_while_asking():
    assert not can_capture(finish_capture(Session(1, "x")))


def test_finish_capture_twice_fails():
    with pytest.raises(SessionError):
        finish_capture(finish_capture(Session(1, "x")))


def test_record_answer_without_question_fails():
    with pytest.raises(SessionError):
        record_answer(Session(1, "x", status=CAPTURING))


def test_cancel_active_but_not_finished():
    assert cancel(Session(1, "x")).status == CANCELLED
    with pytest.raises(SessionError):
        cancel(Session(1, "x", status=DRAFTED))


@pytest.mark.parametrize("text", ["skip", " Skip. ", "-", "none", ""])
def test_skip_answers(text):
    assert normalize_answer(text) is None


def test_real_answer_kept():
    assert normalize_answer("  Met Ahmad from Binance ") == "Met Ahmad from Binance"


def test_event_name_cleaned():
    assert clean_event_name("  ETH   KL  Meetup ") == "ETH KL Meetup"
    with pytest.raises(SessionError):
        clean_event_name("   ")
