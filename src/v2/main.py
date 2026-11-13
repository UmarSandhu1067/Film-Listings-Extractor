"""Command-line entry point for the V2 extractor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.v2.extractor import write_json
from src.v2.layout import LayoutDetectionError


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract Sheet D listings with V2.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.pdf.is_file():
        print(f"Error: input PDF not found: {args.pdf}", file=sys.stderr)
        return 1
    try:
        result = write_json(args.pdf, args.out)
    except LayoutDetectionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {len(result.projects)} project(s) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(cli())
