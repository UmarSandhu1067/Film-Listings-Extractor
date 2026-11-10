"""Read PDF pages and expose every word with its page coordinates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pdfplumber


def read_pdf(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Extract page text and positioned words.

    Coordinates are in PDF points, with ``x0``, ``x1``, ``top``, and
    ``bottom`` measured relative to the page's top-left corner.
    """
    pages: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            words = [
                {
                    "text": str(word["text"]),
                    "x0": float(word["x0"]),
                    "x1": float(word["x1"]),
                    "top": float(word["top"]),
                    "bottom": float(word["bottom"]),
                }
                for word in page.extract_words()
                if str(word.get("text", "")).strip()
            ]
            pages.append(
                {
                    "page_number": page_number,
                    "width": float(page.width),
                    "height": float(page.height),
                    "text": page.extract_text() or "",
                    "words": words,
                }
            )
    return pages


def print_word_coordinates(pages: list[dict[str, Any]]) -> None:
    """Print every extracted word and its bounding coordinates."""
    for page in pages:
        print(f"Page {page['page_number']} ({page['width']:.1f} x {page['height']:.1f} pt)")
        for word in page["words"]:
            print(
                f"  {word['text']!r:<32} "
                f"x0={word['x0']:7.1f} x1={word['x1']:7.1f} "
                f"top={word['top']:7.1f} bottom={word['bottom']:7.1f}"
            )


def print_pdf_words(pdf_path: str | Path) -> None:
    """Read a PDF and print all words with their coordinates."""
    print_word_coordinates(read_pdf(pdf_path))
