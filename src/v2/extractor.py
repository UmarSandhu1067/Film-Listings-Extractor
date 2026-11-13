"""V2 Sheet D extraction and JSON document assembly."""

from __future__ import annotations

import json
from pathlib import Path

from src.pdf_reader import read_pdf
from src.v2.entities import merge_people_companies
from src.v2.layout import LayoutDetectionError, detect_sheet_d, iter_sheet_d_lines
from src.v2.models import V2Company, V2Document, V2Person, V2Project
from src.v2.parser import parse_sheet_d


def extract_document(pdf_path: str | Path) -> V2Document:
    pages = read_pdf(pdf_path)
    if not detect_sheet_d(pages):
        raise LayoutDetectionError("Input PDF is not the supported Sheet D layout.")

    projects = [
        V2Project.model_validate(project)
        for project in parse_sheet_d(iter_sheet_d_lines(pages))
    ]
    project_data = [project.model_dump(mode="python") for project in projects]
    people, companies = merge_people_companies(project_data)
    return V2Document(
        projects=projects,
        people=[V2Person.model_validate(person) for person in people],
        companies=[V2Company.model_validate(company) for company in companies],
    )


def write_json(pdf_path: str | Path, output_path: str | Path) -> V2Document:
    result = extract_document(pdf_path)
    Path(output_path).write_text(
        json.dumps(
            result.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return result
