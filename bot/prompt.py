"""Builds the drafting prompt and parses the model's JSON reply. Pure logic."""

import json
import re
from dataclasses import dataclass

LINKEDIN_MAX_CHARS = 3000
X_MAX_CHARS = 280
MAX_STYLE_SAMPLES = 10

# Generic phrases that make posts read as AI or corporate filler. Some appear in the
# user's own past posts; the prompt says to avoid them anyway.
BANNED_PHRASES = [
    "I'm thrilled", "excited to share", "humbled", "humbling", "journey", "privilege",
    "eye-opening", "incredible chapter", "valuable learning opportunities", "fast-paced",
    "deep exposure", "purpose-driven", "delve", "game-changer", "unlock", "elevate",
    "synergy", "landscape", "tapestry", "it's been a while",
]


@dataclass(frozen=True)
class DraftInputs:
    event_name: str
    notes: list[str]
    photo_captions: list[str]  # one entry per photo, "" if no caption; photos sent in this order
    answers: dict[str, str | None]  # question key -> answer, None if skipped
    style_samples: list[str]


@dataclass(frozen=True)
class Draft:
    short: str
    long: str
    x_post: str
    best_photo: int | None  # 1-based photo number, None if no photos or none suitable
    best_photo_reason: str


class DraftParseError(Exception):
    pass


def _section(title: str, body: str) -> str:
    return f"## {title}\n{body.strip()}\n"


def build_draft_prompt(inputs: DraftInputs) -> str:
    parts = [
        "You turn one person's raw event notes into social posts written in THEIR voice.",
        "",
        "Hard rules:",
        "- Use ONLY facts in the event material below. Never invent names, companies, "
        "numbers, quotes, dates or outcomes. If something is missing, leave it out.",
        "- Match the voice of the style samples: warmth, gratitude, how they thank people, "
        "emoji habits. Do not copy their content. Where the samples are wordy or use "
        "stock phrases, write tighter than them.",
        f"- Never use these phrases, even if the samples do: {', '.join(BANNED_PHRASES)}.",
        "- Plain text only. No markdown, no bold, no links. At most 3 specific hashtags.",
        "",
        "What makes the post work:",
        "- Hook: the first line is the most specific or surprising thing in the material "
        "(a moment, a contrast, a concrete result). Never open with throat-clearing like "
        "'Still wrapping my head around' or 'It's been a while'.",
        "- Specific over abstract: prefer a concrete detail from the material to a general "
        "claim. Do not pad thin material; a shorter post is fine.",
        "- Short paragraphs of 1-3 sentences, readable on a phone.",
        "- Thank people by name only if the material names them, near the end.",
        "- The long LinkedIn post ends with one genuine, specific question readers can "
        "answer from their own experience. No engagement bait ('comment YES').",
        "- At most 2 emoji in the LinkedIn posts.",
        "",
    ]

    samples = [s.strip() for s in inputs.style_samples if s.strip()][:MAX_STYLE_SAMPLES]
    if samples:
        joined = "\n\n---\n\n".join(samples)
        parts.append(_section("Style samples (voice reference only)", joined))
    else:
        parts.append(_section(
            "Style samples",
            "None provided. Write plainly and conversationally, first person.",
        ))

    material = [f"Event: {inputs.event_name}"]
    if inputs.notes:
        material.append("Notes taken during the event:")
        material += [f"- {note.strip()}" for note in inputs.notes]
    answer_labels = {
        "takeaway": "Main takeaway",
        "people": "People met",
        "next_step": "What I'll do next",
    }
    for key, label in answer_labels.items():
        answer = inputs.answers.get(key)
        if answer:
            material.append(f"{label}: {answer.strip()}")
    parts.append(_section("Event material (the ONLY source of facts)", "\n".join(material)))

    if inputs.photo_captions:
        lines = []
        for i, caption in enumerate(inputs.photo_captions, start=1):
            lines.append(f"Photo {i}: {caption.strip() or '(no caption)'}")
        parts.append(_section(
            "Photos (attached in this order)",
            "\n".join(lines) + "\nUse photos for context only. Do not name people "
            "in photos unless the event material names them.",
        ))

    parts.append(_section("Output", (
        "Reply with JSON only, with these keys:\n"
        '"short": LinkedIn post, 300-600 characters.\n'
        f'"long": LinkedIn post, 800-{LINKEDIN_MAX_CHARS - 500} characters.\n'
        f'"x_post": X/Twitter post, at most {X_MAX_CHARS} characters.\n'
        '"best_photo": number of the best photo for the post, or null if there are none.\n'
        '"best_photo_reason": one short sentence, or "" if best_photo is null.'
    )))
    return "\n".join(parts)


def _strip_code_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return match.group(1) if match else text


def parse_draft_response(text: str, photo_count: int) -> Draft:
    try:
        data = json.loads(_strip_code_fence(text).strip())
    except json.JSONDecodeError as exc:
        raise DraftParseError(f"Model did not return valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DraftParseError("Model reply is not a JSON object.")

    fields = {}
    for key in ("short", "long", "x_post"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise DraftParseError(f"Model reply is missing '{key}'.")
        fields[key] = value.strip()

    best_photo = data.get("best_photo")
    if not isinstance(best_photo, int) or isinstance(best_photo, bool) \
            or not 1 <= best_photo <= photo_count:
        best_photo = None
    reason = data.get("best_photo_reason") if best_photo else ""

    return Draft(
        short=fields["short"],
        long=fields["long"][:LINKEDIN_MAX_CHARS],
        x_post=fields["x_post"],
        best_photo=best_photo,
        best_photo_reason=reason.strip() if isinstance(reason, str) else "",
    )
