"""Send extracted project records to the batch API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx

from src.api import BATCH_SIZE


def _read_projects(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError("The result JSON must be an object containing 'projects'.")
    projects = document.get("projects")
    if not isinstance(projects, list) or not all(isinstance(item, dict) for item in projects):
        raise TypeError("'projects' must be a list of JSON objects.")
    if not projects:
        raise ValueError("The result JSON contains no projects to send.")
    return projects


def _send_batches(projects: list[dict[str, Any]], base_url: str) -> tuple[int, int]:
    total_accepted = 0
    total_rejected = 0
    projects_url = f"{base_url.rstrip('/')}/projects"
    with httpx.Client() as client:
        for start in range(0, len(projects), BATCH_SIZE):
            batch_number = start // BATCH_SIZE + 1
            batch = projects[start : start + BATCH_SIZE]
            response = client.post(projects_url, json={"projects": batch})
            response.raise_for_status()
            result = response.json()
            accepted = result["accepted"]
            rejected = len(result["rejected"])
            total_accepted += accepted
            total_rejected += rejected
            print(f"Batch {batch_number}: accepted={accepted}, rejected={rejected}")

    return total_accepted, total_rejected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send result.json projects to the batch API.")
    parser.add_argument("result", type=Path, help="extractor result JSON path")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="API base URL",
    )
    args = parser.parse_args(argv)

    projects = _read_projects(args.result)
    accepted, rejected = _send_batches(projects, args.url)
    print(f"Total: accepted={accepted}, rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
