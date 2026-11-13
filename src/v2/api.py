"""Independent V2 FastAPI sub-application mounted at ``/v2``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

from src.v2.entities import merge_people_companies
from src.v2.extractor import extract_document
from src.v2.models import V2Company, V2Person, V2Project

BATCH_SIZE = 20
DEFAULT_INPUT_PDF = (
    Path(__file__).resolve().parents[2] / "input" / "sheet_d_two_column_grid.pdf"
)
app = FastAPI(title="Film Listings Extractor API V2")
_accepted_projects: list[V2Project] = []


def load_default_projects() -> None:
    document = extract_document(DEFAULT_INPUT_PDF)
    _accepted_projects[:] = document.projects


class ProjectsBatch(BaseModel):
    projects: list[dict[str, Any]]


class RejectedProject(BaseModel):
    index: int
    errors: list[str]


class BatchResult(BaseModel):
    accepted: int
    rejected: list[RejectedProject]


class HealthResult(BaseModel):
    status: str


@app.post("/projects", response_model=BatchResult)
def post_projects(batch: ProjectsBatch) -> BatchResult:
    project_count = len(batch.projects)
    if project_count == 0:
        raise HTTPException(status_code=422, detail="At least one project is required")
    if project_count > BATCH_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Max {BATCH_SIZE} projects per request, got {project_count}",
        )

    rejected: list[RejectedProject] = []
    accepted = 0
    project_indices = {
        project.project_title_cleaned.casefold(): index
        for index, project in enumerate(_accepted_projects)
    }
    for index, record in enumerate(batch.projects):
        try:
            project = V2Project.model_validate(record)
        except ValidationError as exc:
            errors = [
                f"{'.'.join(str(part) for part in error['loc']) or 'record'}: {error['msg']}"
                for error in exc.errors()
            ]
            rejected.append(RejectedProject(index=index, errors=errors))
            continue

        identity = project.project_title_cleaned.casefold()
        existing_index = project_indices.get(identity)
        if existing_index is None:
            project_indices[identity] = len(_accepted_projects)
            _accepted_projects.append(project)
        else:
            _accepted_projects[existing_index] = project
        accepted += 1

    return BatchResult(accepted=accepted, rejected=rejected)


@app.get(
    "/projects",
    response_model=list[V2Project],
    response_model_exclude_none=True,
)
def get_projects() -> list[V2Project]:
    return _accepted_projects


@app.get("/people", response_model=list[V2Person])
def get_people() -> list[V2Person]:
    projects = [project.model_dump(mode="python") for project in _accepted_projects]
    people, _ = merge_people_companies(projects)
    return [V2Person.model_validate(person) for person in people]


@app.get("/companies", response_model=list[V2Company])
def get_companies() -> list[V2Company]:
    projects = [project.model_dump(mode="python") for project in _accepted_projects]
    _, companies = merge_people_companies(projects)
    return [V2Company.model_validate(company) for company in companies]


@app.get("/health", response_model=HealthResult)
def get_health() -> HealthResult:
    return HealthResult(status="ok")
