"""Parse Sheet A PDFs, whose project fields are introduced by labels."""

from __future__ import annotations

import re
from typing import Any

from src.parsers._common import (
    append_value,
    line_groups,
    line_text,
    new_project,
    new_role,
    role_from_line,
    text_slice,
)

_FIELD_RE = re.compile(
    r"^\s*(Studio|Genre|Location|Start\s+Date|Status|Synopsis)\s*:\s*",
    re.IGNORECASE,
)
_FIELD_MAP = {
    "studio": "studio",
    "genre": "genre",
    "location": "location",
    "start date": "start_date",
    "status": "status",
    "synopsis": "synopsis",
}


def parse_sheet_a(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract projects and role descriptions from labelled-field pages."""
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
            if folded.startswith("studio slate") or re.fullmatch(r"page\s+\d+", folded):
                previous_top = None
                continue
            if re.match(r"^\((?:fka|aka)\b", folded) and current:
                previous_top = top
                continue

            field_match = _FIELD_RE.match(text)
            if field_match and current:
                field = _FIELD_MAP[re.sub(r"\s+", " ", field_match.group(1).casefold())]
                append_value(current, field, text_slice(line, field_match.end(), len(text)))
                previous_field = field
                in_roles = False
                previous_top = top
                continue

            if re.match(r"^\s*roles\s*:", folded):
                in_roles = True
                previous_field = None
                previous_top = top
                continue

            gap = top - previous_top if previous_top is not None else 0
            role = role_from_line(line) if in_roles else None
            if in_roles and current and gap >= 28 and role is None:
                current = new_project(text.strip())
                projects.append(current)
                previous_field = None
                in_roles = False
                previous_top = top
                continue

            if in_roles and current:
                if role:
                    current["roles"].append(role)
                elif current["roles"]:
                    last_role = current["roles"][-1]
                    description = text.strip()
                    if description:
                        if last_role["gender"] is None and last_role["age"] is None:
                            last_role.update(
                                new_role(
                                    last_role["role_name"],
                                    last_role["role_type"],
                                    description,
                                )
                            )
                        else:
                            last_role["notes"] = (
                                f"{last_role['notes']} {description}" if last_role["notes"] else description
                            )
                previous_top = top
                continue

            if current and previous_field == "synopsis" and gap <= 24:
                append_value(current, "synopsis", text.strip())
                previous_top = top
                continue

            if current is None or gap >= 28:
                title = text.strip()
                if title:
                    current = new_project(title)
                    projects.append(current)
                    previous_field = None
                    in_roles = False
            previous_top = top

    return projects
