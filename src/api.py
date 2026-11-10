"""Batch API for validating and inspecting extracted projects."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.models import Project

BATCH_SIZE = 20

app = FastAPI(title="Film Listings Extractor API")
_accepted_projects: list[Project] = []


class ProjectsBatch(BaseModel):
    """Request body containing raw project records."""

    projects: list[dict[str, Any]]


class RejectedProject(BaseModel):
    """Validation errors for one project in a submitted batch."""

    index: int
    errors: list[str]


class BatchResult(BaseModel):
    """Counts for a single submitted batch."""

    accepted: int
    rejected: list[RejectedProject]


class HealthResult(BaseModel):
    """API health response."""

    status: str


@app.post("/projects", response_model=BatchResult)
def post_projects(batch: ProjectsBatch) -> BatchResult:
    """Validate project records independently and store valid records."""
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
    for index, record in enumerate(batch.projects):
        try:
            project = Project.model_validate(record)
        except ValueError as exc:
            errors = [
                f"{'.'.join(str(part) for part in error['loc']) or 'record'}: {error['msg']}"
                for error in exc.errors()
            ]
            rejected.append(RejectedProject(index=index, errors=errors))
        else:
            _accepted_projects.append(project)
            accepted += 1

    return BatchResult(accepted=accepted, rejected=rejected)


@app.get("/projects", response_model=list[Project])
def get_projects() -> list[Project]:
    """Return all projects accepted since the service started."""
    return _accepted_projects


@app.get("/health", response_model=HealthResult)
def get_health() -> HealthResult:
    """Report that the API is ready to receive requests."""
    return HealthResult(status="ok")
