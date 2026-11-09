"""Parse Sheet B table rows and associate role rows with their project."""

from __future__ import annotations

import re
from typing import Any

from src.parsers._common import line_groups, line_text, new_project, new_role

_COLUMN_NAMES = (
    "project_title",
    "project_type",
    "genre",
    "location",
    "start_date",
    "role_name",
    "role_type",
    "notes",
)
_HEADER_RE = re.compile(
    r"\bTitle\b.*\bType\b.*\bGenre\b.*\bLocation\b.*\bStart\b.*"
    r"\bRole\b.*\bRole\s+Type\b",
    re.IGNORECASE,
)


def _header_columns(line: list[dict[str, Any]]) -> tuple[float, ...] | None:
    ordered = sorted(line, key=lambda word: word["x0"])
    positions: dict[str, float] = {}
    role_positions: list[float] = []
    genre_position: float | None = None
    type_positions: list[float] = []
    for word in ordered:
        token = str(word["text"]).casefold()
        if token in {"title", "genre", "location", "start", "notes"}:
            positions.setdefault(token, word["x0"])
        elif token == "type":
            type_positions.append(word["x0"])
        elif token == "role":
            role_positions.append(word["x0"])
        if token == "genre":
            genre_position = word["x0"]

    project_type = next(
        (position for position in type_positions if genre_position and position < genre_position),
        None,
    )
    if (
        project_type is None
        or len(role_positions) < 2
        or any(name not in positions for name in ("title", "genre", "location", "start", "notes"))
    ):
        return None
    return (
        positions["title"],
        project_type,
        positions["genre"],
        positions["location"],
        positions["start"],
        role_positions[0],
        role_positions[1],
        positions["notes"],
    )


def _columns(line: list[dict[str, Any]], column_starts: tuple[float, ...]) -> dict[str, list[dict[str, Any]]]:
    cells = {name: [] for name in _COLUMN_NAMES}
    current_column: int | None = None
    for word in line:
        aligned_column = min(
            range(len(column_starts)),
            key=lambda column: abs(word["x0"] - column_starts[column]),
        )
        if abs(word["x0"] - column_starts[aligned_column]) <= 2.5 or current_column is None:
            current_column = aligned_column
        cells[_COLUMN_NAMES[current_column]].append(word)
    return cells


def _cell_text(words: list[dict[str, Any]]) -> str | None:
    return " ".join(str(word["text"]) for word in words).strip() or None


def parse_sheet_b(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Read the fixed grid columns; rows without a title add roles to the current project."""
    projects: list[dict[str, Any]] = []
    for page in pages:
        header_seen = False
        column_starts: tuple[float, ...] | None = None
        current: dict[str, Any] | None = None
        for line in line_groups(page["words"]):
            if _HEADER_RE.search(line_text(line)):
                header_seen = True
                column_starts = _header_columns(line)
                continue
            if not header_seen or column_starts is None:
                continue

            cells = {name: _cell_text(words) for name, words in _columns(line, column_starts).items()}
            if cells["project_title"]:
                current = new_project(cells["project_title"])
                for field in ("project_type", "genre", "location", "start_date"):
                    current[field] = cells[field]
                projects.append(current)

            if current and cells["role_name"]:
                current["roles"].append(
                    new_role(
                        cells["role_name"],
                        cells["role_type"],
                        cells["notes"],
                    )
                )
    return projects
