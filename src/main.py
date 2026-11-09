"""End-to-end PDF extraction workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from pprint import pprint
from typing import Any

from src.detector import detect_layout
from src.parsers.sheet_a_parser import parse_sheet_a
from src.parsers.sheet_b_parser import parse_sheet_b
from src.parsers.sheet_c_parser import parse_sheet_c
from src.pdf_reader import read_pdf

_PARSERS = {
    "A": parse_sheet_a,
    "B": parse_sheet_b,
    "C": parse_sheet_c,
}


def extract_projects(pdf_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Read, detect, and parse one PDF into the shared dictionary structure."""
    pages = read_pdf(pdf_path)
    layout = detect_layout(pages)
    projects = _PARSERS[layout](pages)
    return {"projects": projects}


def main(pdf_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Print extracted projects in a readable form and return them."""
    result = extract_projects(pdf_path)
    print(f"Extracted {len(result['projects'])} project(s) from {pdf_path}:")
    pprint(result, sort_dicts=False, width=100)
    return result


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description="Extract project listings from a PDF.")
    argument_parser.add_argument("pdf", type=Path, help="path to a Sheet A, B, or C PDF")
    args = argument_parser.parse_args()
    main(args.pdf)
