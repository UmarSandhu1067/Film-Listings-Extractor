import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import _accepted_projects, app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    _accepted_projects.clear()
    with TestClient(app) as test_client:
        yield test_client
    _accepted_projects.clear()


def _project(title: str) -> dict[str, str]:
    return {"project_title": title}


def test_valid_batch_is_accepted(client):
    response = client.post(
        "/projects",
        json={"projects": [_project("Quiet Hours"), _project("Northbound")]},
    )

    assert response.status_code == 200
    assert response.json() == {"accepted": 2, "rejected": []}


def test_invalid_record_is_rejected_without_rejecting_valid_records(client):
    response = client.post(
        "/projects",
        json={
            "projects": [
                _project("Quiet Hours"),
                {"studio": "North Star"},
                _project("Northbound"),
            ]
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["accepted"] == 2
    assert len(result["rejected"]) == 1
    assert result["rejected"][0]["index"] == 1
    assert any("project_title:" in error for error in result["rejected"][0]["errors"])


def test_exactly_twenty_records_are_accepted(client):
    response = client.post(
        "/projects",
        json={"projects": [_project(f"Project {index}") for index in range(20)]},
    )

    assert response.status_code == 200
    assert response.json() == {"accepted": 20, "rejected": []}


def test_more_than_twenty_records_returns_413(client):
    response = client.post(
        "/projects",
        json={"projects": [_project(f"Project {index}") for index in range(21)]},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Max 20 projects per request, got 21"


def test_empty_batch_returns_422(client):
    response = client.post("/projects", json={"projects": []})

    assert response.status_code == 422
    assert "required" in response.json()["detail"]


def test_pages_key_is_ignored(client):
    response = client.post(
        "/projects",
        json={"projects": [_project("Quiet Hours")], "pages": [{"page_number": 1}]},
    )

    assert response.status_code == 200
    assert response.json() == {"accepted": 1, "rejected": []}


def test_get_projects_returns_accepted_records(client):
    client.post("/projects", json={"projects": [_project("Quiet Hours")]})

    response = client.get("/projects")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["project_title"] == "Quiet Hours"


@pytest.mark.parametrize("filename", ["sheet_a.json", "sheet_b.json", "sheet_c.json"])
def test_extractor_json_projects_round_trip(client, filename):
    document = json.loads((PROJECT_ROOT / filename).read_text(encoding="utf-8"))

    response = client.post("/projects", json={"projects": document["projects"]})

    assert response.status_code == 200
    assert response.json()["accepted"] == len(document["projects"])
    assert response.json()["rejected"] == []
