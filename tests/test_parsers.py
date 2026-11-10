from pathlib import Path

import pytest

from src.main import extract_projects

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "input"
PROJECT_KEYS = {
    "project_title",
    "title_alias",
    "project_type",
    "studio",
    "genre",
    "location",
    "start_date",
    "status",
    "synopsis",
    "network",
    "shoot_location",
    "roles",
}
ROLE_KEYS = {"role_name", "role_type", "gender", "age", "notes"}


@pytest.mark.parametrize(
    ("filename", "project_count", "role_count", "absent_project_keys", "has_title_alias"),
    [
        (
            "sheet_a_labelled_fields.pdf",
            4,
            9,
            {"project_type", "network", "shoot_location"},
            True,
        ),
        (
            "sheet_b_table.pdf",
            5,
            12,
            {"studio", "status", "synopsis", "network", "shoot_location"},
            False,
        ),
        ("sheet_c_messy_text.pdf", 3, 9, {"project_type"}, False),
    ],
)
def test_each_pdf_only_produces_fields_extracted_from_its_layout(
    filename,
    project_count,
    role_count,
    absent_project_keys,
    has_title_alias,
):
    result = extract_projects(INPUT / filename)
    projects = result["projects"]

    assert len(projects) == project_count
    assert sum(len(project["roles"]) for project in projects) == role_count
    for project in projects:
        assert set(project) <= PROJECT_KEYS
        assert absent_project_keys.isdisjoint(project)
        assert isinstance(project["project_title"], str)
        assert ("title_alias" in project) is has_title_alias
        assert isinstance(project["roles"], list)
        assert all(
            value is not None
            for key, value in project.items()
            if key not in {"roles", "title_alias"}
        )
        for role in project["roles"]:
            assert set(role) <= ROLE_KEYS
            assert isinstance(role["role_name"], str)
            assert all(value is not None for value in role.values())


def test_sheet_a_fields_roles_and_missing_values_are_preserved():
    projects = extract_projects(INPUT / "sheet_a_labelled_fields.pdf")["projects"]
    paper_crowns = next(project for project in projects if project["project_title"] == "Paper Crowns")
    quiet_hours = next(project for project in projects if project["project_title"] == "Quiet Hours")

    lantern = next(project for project in projects if project["project_title"] == "THE LANTERN KEEPER")
    assert paper_crowns["studio"] == "Bluecastle Studios"
    assert paper_crowns["genre"] == "Dramedy"
    assert paper_crowns["start_date"] == "2/1/2026"
    assert lantern["title_alias"] == "(fka Lighthouse Song)"
    assert quiet_hours["title_alias"] == "(aka The Night Desk)"
    assert paper_crowns["title_alias"] is None
    assert paper_crowns["roles"][0] == {
        "role_name": "JUNE OKAFOR",
        "role_type": "Lead",
        "gender": "Female",
        "age": "30s",
        "notes": "open ethnicity. The responsible one.",
    }
    assert "studio" not in quiet_hours
    assert "genre" not in quiet_hours


def test_sheet_b_associates_continuation_rows_with_correct_project():
    projects = extract_projects(INPUT / "sheet_b_table.pdf")["projects"]
    midnight_orchard = next(project for project in projects if project["project_title"] == "MIDNIGHT ORCHARD")
    glass_harbor = next(project for project in projects if project["project_title"] == "Glass Harbor")
    summit = next(project for project in projects if project["project_title"] == "SUMMIT")
    static_bloom = next(project for project in projects if project["project_title"] == "Static Bloom")

    assert [role["role_name"] for role in midnight_orchard["roles"]] == [
        "ELSIE",
        "GRANDPA WEBB",
        "DEPUTY ROSS",
    ]
    assert midnight_orchard["roles"][1]["role_type"] == "Supporting"
    assert midnight_orchard["roles"][1]["gender"] == "Male"
    assert midnight_orchard["roles"][1]["age"] == "70s"
    assert glass_harbor["start_date"] == "Q4 2025/Q1 2026"
    assert glass_harbor["roles"][0]["role_name"] == "DET. NORA KIM"
    assert summit["location"] == "Calgary, Alberta, Canada"
    assert summit["start_date"] == "July 13, 2026"
    assert summit["roles"][0]["role_name"] == "COACH DIANE MARSH"
    assert static_bloom["location"] == "TBD (LA, NY or Vancouver)"
    assert static_bloom["start_date"] == "Tent. Summer 2026"


def test_sheet_c_handles_mixed_labels_wrapped_text_and_unusual_role_markers():
    projects = extract_projects(INPUT / "sheet_c_messy_text.pdf")["projects"]
    hollow_creek = next(project for project in projects if project["project_title"] == "HOLLOW CREEK (TV)")
    brass_whistle = next(project for project in projects if project["project_title"] == "the brass whistle")

    assert hollow_creek["network"] == "Riverline / Streamwave"
    assert hollow_creek["start_date"] == "Prob. Nov 2025 to Feb 2026"
    assert hollow_creek["shoot_location"] == "Atlanta, GA and Savannah, GA"
    assert hollow_creek["synopsis"] == (
        "A small-town pharmacist notices the same stranger in every family photo brought in for printing."
    )
    assert "location" not in hollow_creek
    assert hollow_creek["shoot_location"] == "Atlanta, GA and Savannah, GA"
    assert len(brass_whistle["roles"]) == 3
    assert brass_whistle["roles"][0]["role_name"] == "NELL ASHWORTH"
    assert brass_whistle["roles"][0]["role_type"] == "LEAD"
    assert brass_whistle["status"] == "casting"
