"""Parse Sheet D project fields in column-major reading order."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from src.v2.layout import LayoutLine, is_section_band
from src.v2.team import parse_team_lines

_FIELD_RE = re.compile(
    r"\b(Network|Status|Studio|Start|Location|Genre|Logline)\s*:",
    re.IGNORECASE,
)
_FIELD_NAMES = {
    "network": "network",
    "status": "status",
    "studio": "studio",
    "start": "start_date",
    "location": "location",
    "genre": "genre",
    "logline": "synopsis",
}
_ALIAS_RE = re.compile(r"^\s*\((?:fka|aka)\s+([^)]*)\)\s*$", re.IGNORECASE)
_ROLE_RE = re.compile(r".+\s+\[[^]]+\]")
_ROLE_DETAIL_RE = re.compile(r"^(?:Female|Male|Any|Details to come)\b", re.IGNORECASE)
_CONTINUED_RE = re.compile(r"^(.+?)\s+\(continued\)$", re.IGNORECASE)


def _new_project(title: str, section: str | None) -> dict[str, Any]:
    return {
        "project_title": title,
        "section": section,
        "aliases": [],
        "roles": [],
        "credits": [],
    }


def _start_project(
    projects: list[dict[str, Any]],
    title: str,
    section: str | None,
) -> dict[str, Any]:
    project = _new_project(title, section)
    projects.append(project)
    return project


def _append_field(project: dict[str, Any], field: str, value: str) -> None:
    value = value.strip()
    if not value:
        return
    existing = project.get(field)
    project[field] = f"{existing} {value}" if existing else value


def _parse_fields(line: LayoutLine) -> list[tuple[str, str]]:
    matches = list(_FIELD_RE.finditer(line.text))
    result: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(line.text)
        raw = line.text[match.end():end].strip(" \t|:-")
        result.append((_FIELD_NAMES[match.group(1).casefold()], raw))
    return result


def parse_sheet_d(lines: Iterable[LayoutLine]) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    section: str | None = None
    current_field: str | None = None
    in_team = False
    in_roles = False
    team_lines: list[str] = []
    previous_top: float | None = None

    def flush_team() -> None:
        if current and team_lines:
            current["credits"].extend(parse_team_lines(team_lines))
            team_lines.clear()

    for line in lines:
        text = line.text.strip()
        gap = line.top - previous_top if previous_top is not None else 0

        if is_section_band(text):
            flush_team()
            section = text.upper()
            in_team = False
            in_roles = False
            current_field = None
            previous_top = line.top
            continue

        continuation = _CONTINUED_RE.fullmatch(text)
        if (
            continuation
            and current
            and continuation.group(1).casefold() == current["project_title"].casefold()
        ):
            previous_top = line.top
            continue

        alias = _ALIAS_RE.fullmatch(text)
        if alias and current:
            current["title_alias"] = text
            current["aliases"].append(alias.group(1).strip())
            previous_top = line.top
            continue

        if re.match(r"^TEAM\b", text, re.IGNORECASE):
            flush_team()
            in_team = True
            in_roles = False
            current_field = None
            team_lines = []
            remainder = re.sub(r"^TEAM\b", "", text, flags=re.IGNORECASE).strip()
            if remainder:
                team_lines.append(remainder)
            previous_top = line.top
            continue

        if re.fullmatch(r"ROLES\s*:?", text, re.IGNORECASE):
            flush_team()
            in_team = False
            in_roles = True
            current_field = None
            previous_top = line.top
            continue

        fields = _parse_fields(line)
        if fields and current:
            in_team = False
            in_roles = False
            for field, value in fields:
                _append_field(current, field, value)
                current_field = field
            previous_top = line.top
            continue

        if in_team:
            team_lines.append(text)
            previous_top = line.top
            continue

        if in_roles:
            if text.casefold() == "no roles released.":
                previous_top = line.top
                continue
            if _ROLE_RE.fullmatch(text) or _ROLE_DETAIL_RE.match(text):
                previous_top = line.top
                continue
            if current and 0 <= gap < 25:
                previous_top = line.top
                continue
            in_roles = False

        if current and current_field == "synopsis" and gap <= 25:
            _append_field(current, "synopsis", text)
            previous_top = line.top
            continue

        flush_team()
        current = _start_project(projects, text, section)
        current_field = None
        in_team = False
        in_roles = False
        previous_top = line.top

    return projects
