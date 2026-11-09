"""Parse Sheet C free-text notes with inconsistent field order and line breaks."""

from __future__ import annotations

import re
from typing import Any

from src.parsers._common import (
    append_value,
    line_groups,
    line_text,
    new_project,
    role_from_line,
    text_slice,
)

_LABEL_RE = re.compile(
    r"\b(Network|Dates?|Start(?:\s+Date)?|Studio|Genre|Location|Status|Shoot|"
    r"Story|Synopsis|Logline)\s*[:\-]",
    re.IGNORECASE,
)
_FIELD_MAP = {
    "network": "network",
    "date": "start_date",
    "dates": "start_date",
    "start": "start_date",
    "start date": "start_date",
    "studio": "studio",
    "genre": "genre",
    "location": "location",
    "status": "status",
    "shoot": "shoot_location",
    "story": "synopsis",
    "synopsis": "synopsis",
    "logline": "synopsis",
}


def _is_roles_heading(text: str) -> bool:
    return bool(re.fullmatch(r"\s*roles?\s*:?-?\s*", text, re.IGNORECASE))


def parse_sheet_c(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract project blocks, inline labels, continuations, and marked role lines."""
    projects: list[dict[str, Any]] = []
    for page in pages:
        current: dict[str, Any] | None = None
        previous_top: float | None = None
        previous_field: str | None = None
        in_roles = False

        for line in line_groups(page["words"]):
            text = line_text(line)
            folded = text.casefold()
            top = min(word["top"] for word in line)
            if folded.startswith("agency notes"):
                previous_top = None
                continue

            labels = list(_LABEL_RE.finditer(text))
            if labels and current:
                for index, label in enumerate(labels):
                    label_name = re.sub(r"\s+", " ", label.group(1).casefold())
                    field = _FIELD_MAP[label_name]
                    end = labels[index + 1].start() if index + 1 < len(labels) else len(text)
                    raw_value = text[label.end():end]
                    leading = len(raw_value) - len(raw_value.lstrip(" \t|:-"))
                    value = text_slice(line, label.end() + leading, end)
                    if value:
                        value = value.strip(" |")
                    append_value(current, field, value)
                    if field == "shoot_location":
                        append_value(current, "location", value)
                    previous_field = field
                in_roles = False
                previous_top = top
                continue

            if _is_roles_heading(text):
                in_roles = True
                previous_field = None
                previous_top = top
                continue

            gap = top - previous_top if previous_top is not None else 0
            if current and gap >= 25:
                current = new_project(text.strip())
                projects.append(current)
                in_roles = False
                previous_field = None
                previous_top = top
                continue
            if current is None:
                current = new_project(text.strip())
                projects.append(current)
                previous_top = top
                continue

            role = role_from_line(line) if in_roles else None
            if role:
                current["roles"].append(role)
                previous_field = None
                previous_top = top
                continue

            if in_roles:
                previous_top = top
                continue

            if previous_field and gap <= 22:
                append_value(current, previous_field, text.strip())
                if previous_field == "shoot_location":
                    append_value(current, "location", text.strip())
                previous_top = top
                continue

            previous_field = None
            previous_top = top

    return projects
