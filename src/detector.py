"""Identify the supplied labelled-field, table, and free-text PDF layouts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Literal

from src.parsers._common import line_groups, line_text

Layout = Literal["A", "B", "C"]


class LayoutDetectionError(ValueError):
    """Raised when page content does not provide enough evidence for a layout."""


_FIELD_LABELS = re.compile(r"\b(?:Studio|Genre|Location|Start\s+Date)\s*:", re.IGNORECASE)
_FREE_TEXT_LABELS = re.compile(
    r"\b(?:Network|Dates?|Shoot|Story|Synopsis|Logline|Status)\s*[:\-]",
    re.IGNORECASE,
)
_TABLE_HEADERS = re.compile(
    r"\bTitle\b.*\bType\b.*\bGenre\b.*\bLocation\b.*\bStart\b.*"
    r"\bRole\b.*\bRole\s+Type\b",
    re.IGNORECASE,
)


def detect_layout(pages: Sequence[dict[str, Any]]) -> Layout:
    """Detect the layout from first-page text; raise instead of guessing."""
    if not pages or not pages[0].get("words"):
        raise LayoutDetectionError("Cannot detect a PDF layout: the first page has no extractable text.")

    lines = [line_text(line) for line in line_groups(pages[0]["words"])]
    first_page_text = "\n".join(lines)
    folded = first_page_text.casefold()

    if any(_TABLE_HEADERS.search(line) for line in lines):
        return "B"
    if "studio slate" in folded or (
        len(_FIELD_LABELS.findall(first_page_text)) >= 3
        and re.search(r"\bstart\s+date\s*:", first_page_text, re.IGNORECASE)
    ):
        return "A"

    has_role_section = bool(re.search(r"\broles?\b", first_page_text, re.IGNORECASE))
    free_text_fields = len(_FREE_TEXT_LABELS.findall(first_page_text))
    has_project_heading = any(
        line.strip()
        and not _FREE_TEXT_LABELS.match(line)
        and not _FIELD_LABELS.match(line)
        and not re.fullmatch(r"\s*roles?\s*:?\s*", line, re.IGNORECASE)
        for line in lines
    )
    if has_role_section and free_text_fields >= 2 and has_project_heading:
        return "C"

    raise LayoutDetectionError(
        "Could not confidently identify the PDF layout. Expected labelled fields "
        "(Sheet A), a table header (Sheet B), or free-text headings and role sections (Sheet C)."
    )
