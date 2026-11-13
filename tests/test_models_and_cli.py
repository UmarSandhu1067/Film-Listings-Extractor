import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.main import cli, extract_document, write_json
from src.models import Project, Role

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "input"


def test_models_keep_printed_values_while_cleaning_separate_fields():
    project = Project.model_validate(
        {
            "project_title": "  the brass whistle ",
            "genre": "romantic comedy",
            "location": "Likely LA",
            "start_date": "Spring 2026",
            "roles": [
                {
                    "role_name": "NELL ASHWORTH",
                    "role_type": "LEAD",
                    "gender": "female",
                    "age": "20s/30s",
                    "notes": "  open   ethnicity  ",
                }
            ],
        }
    )

    assert project.project_title == "  the brass whistle "
    assert project.project_title_cleaned == "The Brass Whistle"
    assert project.genre == "romantic comedy"
    assert project.genres == ["Romance", "Comedy"]
    assert project.location == "Likely LA"
    assert project.locations == ["Los Angeles"]
    assert project.location_flag is not None
    assert project.start_date == "Spring 2026"
    assert project.start_date_cleaned == date(2026, 3, 1)
    role = project.roles[0]
    assert role.role_type == "LEAD"
    assert role.role_type_cleaned == "Lead"
    assert role.gender == "female"
    assert role.gender_cleaned == "Female"
    assert role.role_name_cleaned == "Nell Ashworth"
    assert role.notes == "  open   ethnicity  "
    assert role.notes_cleaned == "open ethnicity"


@pytest.mark.parametrize(
    ("printed", "cleaned"),
    [
        ("THE LANTERN KEEPER", "The Lantern Keeper"),
        ("SALT AND IRON", "Salt and Iron"),
        ("the brass whistle", "The Brass Whistle"),
    ],
)
def test_project_title_cleaning_preserves_printed_title(printed, cleaned):
    project = Project.model_validate({"project_title": printed})

    assert project.project_title == printed
    assert project.project_title_cleaned == cleaned


def test_models_reject_unexpected_fields():
    with pytest.raises(ValidationError):
        Role.model_validate({"role_name": "JUNE", "unexpected": "value"})


def test_model_keeps_printed_names_and_flags_tbd_roles():
    project = Project.model_validate(
        {
            "project_title": "IRON VALLEY",
            "studio": "OAKMERE FILMS / TANDEM HOUSE",
            "roles": [{"role_name": "TBD ROLE"}],
        }
    )

    assert project.studio == "OAKMERE FILMS / TANDEM HOUSE"
    assert project.studios == ["OAKMERE FILMS", "TANDEM HOUSE"]
    assert project.roles[0].role_name == "TBD ROLE"
    assert project.roles[0].role_name_cleaned == "Tbd Role"
    assert project.roles[0].role_flag == "Role is marked TBD."


@pytest.mark.parametrize(
    ("filename", "expected_genres", "expected_locations"),
    [
        ("sheet_a_labelled_fields.pdf", ("Drama", "Thriller"), ("Los Angeles",)),
        ("sheet_b_table.pdf", ("Horror", "Comedy"), ("New York", "New Jersey")),
        (
            "sheet_c_messy_text.pdf",
            ("Thriller",),
            ("Atlanta", "Savannah"),
        ),
    ],
)
def test_pdf_models_expose_cleaned_project_data(filename, expected_genres, expected_locations):
    result = extract_document(INPUT / filename)
    assert result.projects
    assert result.pages
    assert all(page.text and page.words for page in result.pages)
    assert all(page.page_number == number for number, page in enumerate(result.pages, start=1))
    first = result.projects[0]
    assert tuple(first.genres) == expected_genres
    assert tuple(first.locations) == expected_locations


def test_json_cli_writes_cleaned_data_and_printed_text(tmp_path, capsys):
    output = tmp_path / "result.json"
    code = cli(
        [
            "extract",
            str(INPUT / "sheet_a_labelled_fields.pdf"),
            "--out",
            str(output),
        ]
    )

    document = json.loads(output.read_text(encoding="utf-8"))
    lantern = next(
        project for project in document["projects"] if project["project_title"] == "THE LANTERN KEEPER"
    )
    assert code == 0
    assert lantern["genre"] == "Drama/Thriller"
    assert lantern["genres"] == ["Drama", "Thriller"]
    assert lantern["start_date_cleaned"] == "2026-03-01"
    assert lantern["start_date_precision"] == "season"
    assert lantern["title_alias"] == "(fka Lighthouse Song)"
    first_page = document["pages"][0]
    assert first_page["page_number"] == 1
    assert "STUDIO SLATE - ACTIVE PROJECTS" in first_page["text"]
    assert "Page 1" in first_page["text"]
    assert "characters" not in first_page
    assert any("." in word["text"] for word in first_page["words"])
    assert "Wrote 4 project(s)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("filename", "absent_project_fields"),
    [
        ("sheet_a_labelled_fields.pdf", {"project_type", "network", "shoot_location"}),
        (
            "sheet_b_table.pdf",
            {"studio", "status", "synopsis", "network", "shoot_location"},
        ),
        ("sheet_c_messy_text.pdf", {"project_type"}),
    ],
)
def test_json_output_omits_fields_not_extracted_from_layout(
    tmp_path,
    filename,
    absent_project_fields,
):
    output = tmp_path / "result.json"
    write_json(INPUT / filename, output)

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["projects"]
    assert all(
        absent_project_fields.isdisjoint(project)
        for project in document["projects"]
    )
    if filename == "sheet_a_labelled_fields.pdf":
        assert all("title_alias" in project for project in document["projects"])
    else:
        assert all("title_alias" not in project for project in document["projects"])
    assert all(
        all(value is not None for value in role.values())
        for project in document["projects"]
        for role in project["roles"]
    )
    assert document["pages"]
    assert document["pages"][0]["text"]
    assert set(document["pages"][0]["words"][0]) == {
        "text",
        "x0",
        "x1",
        "top",
        "bottom",
    }


def test_project_has_empty_cleaned_values_for_missing_and_tbd_fields():
    project = Project.model_validate({"project_title": "Quiet Hours", "start_date": "TBD"})
    assert project.studio is None
    assert project.studio_cleaned is None
    assert project.genres == []
    assert project.locations == []
    assert project.start_date_cleaned is None
    assert project.start_date_flag == "Date is marked TBD."
    serialized = project.model_dump(exclude_unset=True)
    assert "studio" not in serialized
    assert "network" not in serialized
    assert "start_date" in serialized
    assert "start_date_cleaned" in serialized
