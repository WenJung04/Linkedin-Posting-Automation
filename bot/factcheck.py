"""Flags names and numbers in a draft that do not appear in the user's own inputs.

Heuristic, not proof: a capitalised word or a number is "unsupported" if the source
text does not contain it. Words that start a sentence are skipped (they are usually
capitalised for grammar, not because they are names), so a made-up name at the very
start of a sentence can slip through. Hashtags are skipped.
"""

import re

ALWAYS_ALLOWED = {"i", "linkedin", "x", "ai"}

_WORD = re.compile(r"#?[A-Za-z][A-Za-z0-9]*")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def _is_sentence_start(text: str, index: int) -> bool:
    before = text[:index].rstrip(" \t\"'“‘(")
    return not before or not (before[-1].isalnum() or before[-1] in ",;&-/")


def _normalize_number(raw: str) -> str:
    return raw.replace(",", "").rstrip(".")


def unsupported_facts(draft: str, source: str) -> list[str]:
    source_lower = source.lower()
    source_numbers = source.replace(",", "")
    flagged: list[str] = []

    for match in _NUMBER.finditer(draft):
        number = _normalize_number(match.group())
        if not re.search(rf"(?<![\d.]){re.escape(number)}(?![\d])", source_numbers):
            flagged.append(match.group())

    for match in _WORD.finditer(draft):
        word = match.group()
        if word.startswith("#") or not word[0].isupper():
            continue
        if word.lower() in ALWAYS_ALLOWED or _is_sentence_start(draft, match.start()):
            continue
        if word.lower() not in source_lower:
            flagged.append(word)

    return list(dict.fromkeys(flagged))  # unique, in order of appearance
