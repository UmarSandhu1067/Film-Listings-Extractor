"""Sheet D layout detection and column-major text ordering."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from src.parsers._common import line_groups, line_text

Column = Literal["left", "right"]


@dataclass(frozen=True)
class LayoutLine:
    page_number: int
    column: Column
    top: float
    text: str


class LayoutDetectionError(ValueError):
    """Raised when page content does not identify Sheet D confidently."""


def detect_sheet_d(pages: Sequence[dict[str, Any]]) -> bool:
    """Recognize the two-column agency grid without reclassifying older sheets."""
    if not pages or not pages[0].get("words"):
        raise LayoutDetectionError("Cannot detect Sheet D: the first page has no extractable text.")

    text = " ".join(str(word["text"]) for word in pages[0]["words"]).casefold()
    return (
        "fernbrook" in text
        and "television" in text
        and "grid" in text
        and "one-hour" in text
        and "team" in text
        and "roles" in text
    )


def iter_sheet_d_lines(pages: Sequence[dict[str, Any]]) -> Iterator[LayoutLine]:
    """Yield page lines in left-column then right-column order, omitting page furniture."""
    for page_number, page in enumerate(pages, start=1):
        words = page["words"]
        width = float(page["width"])
        height = float(page["height"])
        key_top = min(
            (
                float(word["top"])
                for word in words
                if str(word["text"]).casefold().startswith("key:")
            ),
            default=float("inf"),
        )

        columns: tuple[tuple[Column, bool], ...] = (("left", True), ("right", False))
        for column, is_left in columns:
            column_words = [
                word
                for word in words
                if ((float(word["x0"]) + float(word["x1"])) / 2 < width / 2) == is_left
            ]
            for line in line_groups(column_words):
                top = min(float(word["top"]) for word in line)
                if top < 55 or top >= height - 45 or top >= key_top:
                    continue
                text = line_text(line).strip()
                if text:
                    yield LayoutLine(
                        page_number=page_number,
                        column=column,
                        top=top,
                        text=text,
                    )


def is_section_band(text: str) -> bool:
    return bool(re.fullmatch(r"(?:ONE-HOUR|HALF-HOUR) SERIES", text.strip(), re.IGNORECASE))
