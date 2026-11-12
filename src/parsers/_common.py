"""Shared text and record helpers for the layout-specific parsers."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

Word = dict[str, Any]

ROLE_MARKER_RE = re.compile(
    r"\[((?:LEAD|SUPPORTING(?:\s+LEAD)?|RECURRING|CO-STAR|SMALL|GUEST STAR|"
    r"DAY PLAYER|SERIES REGULAR|TBD))\]"
    r"|\(((?:LEAD|SUPPORTING(?:\s+LEAD)?|RECURRING|CO-STAR|SMALL|GUEST STAR|"
    r"DAY PLAYER|SERIES REGULAR|TBD))\)"
    r"|[�\u00B7|]\s*(LEAD|SUPPORTING(?:\s+LEAD)?|RECURRING|CO-STAR|SMALL|"
    r"GUEST STAR|DAY PLAYER|SERIES REGULAR|TBD)\s*[�\u00B7|]",
    re.IGNORECASE,
)
GENDER_RE = re.compile(
    r"\b(any\s+gender|any(?!\s+(?:ethnicity|age))|female|male)\b",
    re.IGNORECASE,
)
AGE_RE = re.compile(
    r"\b(?:late\s+)?\d{1,2}s(?:[-/]\d{1,2}s)?\b"
    r"|\b\d{1,2}[-/]\d{1,2}\b|\bteens\b|\bany age\b",
    re.IGNORECASE,
)


def line_groups(words: Sequence[Word], tolerance: float = 3.0) -> list[list[Word]]:
    """Group extracted words by vertical position, then sort each line left to right."""
    groups: list[list[Word]] = []
    centers: list[float] = []
    for word in sorted(words, key=lambda item: ((item["top"] + item["bottom"]) / 2, item["x0"])):
        center = (word["top"] + word["bottom"]) / 2
        if not groups or abs(center - centers[-1]) > tolerance:
            groups.append([word])
            centers.append(center)
        else:
            groups[-1].append(word)
            centers[-1] = sum((item["top"] + item["bottom"]) / 2 for item in groups[-1]) / len(groups[-1])
    for group in groups:
        group.sort(key=lambda item: item["x0"])
    return groups


def line_text(words: Sequence[Word]) -> str:
    return " ".join(str(word["text"]) for word in words)


def text_slice(words: Sequence[Word], start: int, end: int) -> str | None:
    """Return original extracted word text overlapping a character range."""
    offsets: list[tuple[int, int, Word]] = []
    cursor = 0
    for word in words:
        text = str(word["text"])
        offsets.append((cursor, cursor + len(text), word))
        cursor += len(text) + 1
    selected = [word["text"] for left, right, word in offsets if right > start and left < end]
    value = " ".join(str(part) for part in selected).strip()
    return value or None


def new_project(title: str) -> dict[str, Any]:
    return {"project_title": title, "roles": []}


def _role_attributes(details: str | None) -> tuple[str | None, str | None, str | None]:
    if not details:
        return None, None, None
    gender_match = GENDER_RE.search(details)
    age_match = AGE_RE.search(details)
    gender = gender_match.group(0) if gender_match else None
    age = age_match.group(0) if age_match else None
    spans = sorted(
        (match.span() for match in (gender_match, age_match) if match),
        reverse=True,
    )
    notes = details
    for start, end in spans:
        notes = notes[:start] + notes[end:]
    notes = re.sub(r"^[\s,;:.\-\u2013]+", "", notes)
    notes = re.sub(r"[\s,;:\-\u2013]+$", "", notes)
    return gender, age, notes or None


def new_role(name: str, role_type: str | None = None, details: str | None = None) -> dict[str, Any]:
    gender, age, notes = _role_attributes(details)
    role: dict[str, Any] = {"role_name": name}
    for field, value in (
        ("role_type", role_type),
        ("gender", gender),
        ("age", age),
        ("notes", notes),
    ):
        if value is not None:
            role[field] = value
    return role


def role_from_line(words: Sequence[Word]) -> dict[str, Any] | None:
    """Parse a role name and inline role marker/details from one positioned line."""
    text = line_text(words)
    marker = ROLE_MARKER_RE.search(text)
    if not marker:
        return None
    name_end = marker.start()
    name_start_match = re.match(r"^\s*[-\u2013\u2022]\s*", text)
    if name_start_match:
        name_start = name_start_match.end()
    else:
        name_start = 0
    name = text_slice(words, name_start, name_end)
    if not name:
        return None
    role_type = next((value for value in marker.groups() if value), None)
    details = text_slice(words, marker.end(), len(text))
    return new_role(name, role_type, details)


def append_value(project: dict[str, Any], field: str, value: str | None) -> None:
    if value is None:
        return
    existing = project.get(field)
    project[field] = f"{existing} {value}" if existing else value
