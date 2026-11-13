import pytest
from fastapi.testclient import TestClient

from src.api import _accepted_projects as accepted_v1
from src.api import app as app_v1
from src.v2.api import _accepted_projects as accepted_v2
from src.v2.api import app as app_v2


@pytest.fixture
def clients():
    with TestClient(app_v1) as v1, TestClient(app_v2) as v2:
        accepted_v1.clear()
        accepted_v2.clear()
        yield v1, v2
    accepted_v1.clear()
    accepted_v2.clear()


def _person_credit(name: str, **fields: str) -> dict[str, str]:
    return {"kind": "person", "name": name, **fields}


def test_v1_and_v2_apps_remain_independently_available(clients):
    v1, v2 = clients

    v1_response = v1.post("/projects", json={"projects": [{"project_title": "Same Title"}]})
    v2_response = v2.post(
        "/projects",
        json={
            "projects": [
                {
                    "project_title": "Same Title",
                    "credits": [_person_credit("Jane Sample")],
                }
            ]
        },
    )

    assert v1_response.json() == {"accepted": 1, "rejected": []}
    assert v2_response.json() == {"accepted": 1, "rejected": []}
    assert "credits" not in v1.get("/projects").json()[0]
    assert v2.get("/projects").json()[0]["credits"][0]["name"] == "Jane Sample"
    assert v1.get("/health").json() == {"status": "ok"}
    assert v2.get("/health").json() == {"status": "ok"}


def test_v2_is_available_under_v1_app_prefix_on_one_server(clients):
    v1, _ = clients

    response = v1.post(
        "/v2/projects",
        json={
            "projects": [
                {
                    "project_title": "Mounted V2 Project",
                    "credits": [_person_credit("Jane Sample")],
                }
            ]
        },
    )

    assert response.json() == {"accepted": 1, "rejected": []}
    assert v1.get("/projects").json() == []
    assert v1.get("/v2/projects").json()[0]["project_title"] == "Mounted V2 Project"
    assert v1.get("/v2/people").json()[0]["name"] == "Jane Sample"
    assert v1.get("/v2/companies").json() == []
    assert v1.get("/v2/health").json() == {"status": "ok"}


def test_combined_app_loads_v2_data_at_startup_without_populating_v1():
    accepted_v1.clear()
    accepted_v2.clear()

    with TestClient(app_v1) as client:
        assert len(client.get("/projects").json()) == 0
        assert len(client.get("/v2/projects").json()) == 8
        assert len(client.get("/v2/people").json()) == 17
        assert len(client.get("/v2/companies").json()) == 2

    accepted_v1.clear()
    accepted_v2.clear()


def test_v2_rejects_broken_credits_per_record_and_continues_batch(clients):
    _, v2 = clients
    response = v2.post(
        "/projects",
        json={
            "projects": [
                {"project_title": "Accepted One"},
                {
                    "project_title": "Blank Name",
                    "credits": [_person_credit(" ")],
                },
                {
                    "project_title": "Unknown Kind",
                    "credits": [{"kind": "agency", "name": "Sample Agency"}],
                },
                {"project_title": "Accepted Two"},
            ]
        },
    )

    result = response.json()
    assert result["accepted"] == 2
    assert [item["index"] for item in result["rejected"]] == [1, 2]
    assert any("name must not be blank" in error for error in result["rejected"][0]["errors"])
    assert any("kind" in error for error in result["rejected"][1]["errors"])
    assert [project["project_title"] for project in v2.get("/projects").json()] == [
        "Accepted One",
        "Accepted Two",
    ]


def test_v2_people_endpoint_merges_names_and_contacts_across_loads(clients):
    _, v2 = clients
    first = v2.post(
        "/projects",
        json={
            "projects": [
                {
                    "project_title": "First Project",
                    "credits": [
                        _person_credit(
                            "Jane-Sample",
                            phone="(212) 555-0100",
                            email="JANE@EXAMPLE.TEST",
                        )
                    ],
                }
            ]
        },
    )
    second = v2.post(
        "/projects",
        json={
            "projects": [
                {
                    "project_title": "Second Project",
                    "credits": [_person_credit("jane sample", email="jane2@example.test")],
                }
            ]
        },
    )

    people = v2.get("/people").json()
    assert first.json()["accepted"] == second.json()["accepted"] == 1
    assert len(people) == 1
    assert people[0]["person_key"] == "jane-sample"
    assert people[0]["phones"] == ["+12125550100"]
    assert people[0]["emails"] == ["jane@example.test", "jane2@example.test"]
    assert people[0]["projects"] == ["First Project", "Second Project"]


def test_v2_batch_limits_match_the_existing_api_contract(clients):
    _, v2 = clients

    empty = v2.post("/projects", json={"projects": []})
    too_many = v2.post(
        "/projects",
        json={"projects": [{"project_title": f"Project {index}"} for index in range(21)]},
    )

    assert empty.status_code == 422
    assert too_many.status_code == 413
    assert too_many.json()["detail"] == "Max 20 projects per request, got 21"
