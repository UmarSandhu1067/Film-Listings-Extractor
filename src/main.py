"""End-to-end PDF extraction workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from pprint import pprint
from typing import Any

from src.detector import detect_layout
from src.models import ExtractionResult, PDFPage, Project
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
    """Read, detect, and parse a PDF using its layout-specific field set."""
    _, projects = _read_and_parse(pdf_path)
    return {"projects": projects}


def _read_and_parse(pdf_path: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read each PDF page once and parse its project listings."""
    pages = read_pdf(pdf_path)
    layout = detect_layout(pages)
    projects = _PARSERS[layout](pages)
    return pages, projects


def main(pdf_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Print extracted projects in a readable form and return them."""
    result = extract_projects(pdf_path)
    print(f"Extracted {len(result['projects'])} project(s) from {pdf_path}:")
    pprint(result, sort_dicts=False, width=100)
    return result


def extract_document(pdf_path: str | Path) -> ExtractionResult:
    """Return page-level source text and validated projects with cleaned values."""
    pages, projects = _read_and_parse(pdf_path)
    return ExtractionResult(
        projects=[Project.model_validate(project) for project in projects],
        pages=[PDFPage.model_validate(page) for page in pages],
    )


def write_json(pdf_path: str | Path, output_path: str | Path) -> ExtractionResult:
    """Write extracted pages and layout-specific project data as UTF-8 JSON."""
    result = extract_document(pdf_path)
    Path(output_path).write_text(
        json.dumps(
            result.model_dump(mode="json", exclude_unset=True),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def cli(argv: list[str] | None = None) -> int:
    """Run the extractor CLI; retain the earlier one-argument print workflow."""
    parser = argparse.ArgumentParser(description="Extract project listings from a PDF.")
    parser.add_argument("command_or_pdf", help="'extract' or a PDF path")
    parser.add_argument("pdf", nargs="?", type=Path, help="PDF path after the 'extract' command")
    parser.add_argument("--out", type=Path, help="write the extracted projects to JSON")
    args = parser.parse_args(argv)

    if args.command_or_pdf == "extract":
        if args.pdf is None:
            parser.error("'extract' requires a PDF path.")
        if args.out is None:
            parser.error("'extract' requires --out JSON_PATH.")
        result = write_json(args.pdf, args.out)
        print(f"Wrote {len(result.projects)} project(s) to {args.out}")
        return 0

    if args.pdf is not None:
        parser.error("Use 'extract PDF --out JSON_PATH' for JSON output.")
    if args.out is not None:
        result = write_json(args.command_or_pdf, args.out)
        print(f"Wrote {len(result.projects)} project(s) to {args.out}")
    else:
        main(args.command_or_pdf)
    return 0


if __name__ == "__main__":
    sys.exit(cli())
