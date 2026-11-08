import json

import pytest

from bot.prompt import DraftInputs, DraftParseError, build_draft_prompt, parse_draft_response


def make_inputs(**overrides):
    values = dict(
        event_name="ETH KL Meetup",
        notes=["Panel on stablecoin regulation", "Gas fees came up a lot"],
        photo_captions=["stage panel", ""],
        answers={"takeaway": "Regulation is coming fast", "people": None, "next_step": "Read MiCA"},
        style_samples=["Sample post one.", "Sample post two."],
    )
    values.update(overrides)
    return DraftInputs(**values)


def test_prompt_contains_all_material():
    prompt = build_draft_prompt(make_inputs())
    for expected in ["ETH KL Meetup", "Panel on stablecoin regulation", "Regulation is coming fast",
                     "Read MiCA", "Photo 1: stage panel", "Photo 2: (no caption)",
                     "Sample post one.", "Sample post two."]:
        assert expected in prompt


def test_skipped_answers_are_left_out():
    prompt = build_draft_prompt(make_inputs())
    assert "People met" not in prompt


def test_no_photos_section_without_photos():
    assert "Photo 1" not in build_draft_prompt(make_inputs(photo_captions=[]))


def test_missing_style_samples_noted():
    prompt = build_draft_prompt(make_inputs(style_samples=["  "]))
    assert "None provided" in prompt


def test_style_samples_capped_at_ten():
    samples = [f"post {i}" for i in range(15)]
    prompt = build_draft_prompt(make_inputs(style_samples=samples))
    assert "post 9" in prompt and "post 10" not in prompt


def test_prompt_forbids_invention():
    assert "Never invent" in build_draft_prompt(make_inputs())


def reply(**overrides):
    data = {"short": "s", "long": "l", "x_post": "x", "best_photo": 2, "best_photo_reason": "clear"}
    data.update(overrides)
    return json.dumps(data)


def test_parse_valid_reply():
    draft = parse_draft_response(reply(), photo_count=2)
    assert (draft.short, draft.long, draft.x_post, draft.best_photo) == ("s", "l", "x", 2)
    assert draft.best_photo_reason == "clear"


def test_parse_strips_code_fence():
    draft = parse_draft_response(f"```json\n{reply()}\n```", photo_count=2)
    assert draft.short == "s"


@pytest.mark.parametrize("best_photo", [0, 3, "1", True, None])
def test_out_of_range_photo_becomes_none(best_photo):
    draft = parse_draft_response(reply(best_photo=best_photo), photo_count=2)
    assert draft.best_photo is None and draft.best_photo_reason == ""


def test_long_post_capped_at_linkedin_limit():
    assert len(parse_draft_response(reply(long="a" * 5000), 0).long) == 3000


@pytest.mark.parametrize("bad", ["not json", "[1, 2]", reply(short=""), reply(x_post=None)])
def test_bad_replies_raise(bad):
    with pytest.raises(DraftParseError):
        parse_draft_response(bad, photo_count=0)
