import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.main import cli, extract_document
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
    assert project.project_title_cleaned == "the brass whistle"
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
    assert role.notes == "  open   ethnicity  "
    assert role.notes_cleaned == "open ethnicity"


def test_models_reject_unexpected_fields():
    with pytest.raises(ValidationError):
        Role.model_validate({"role_name": "JUNE", "unexpected": "value"})


@pytest.mark.parametrize(
    ("filename", "expected_genres", "expected_locations"),
    [
        ("sheet_a_labelled_fields.pdf", ("Drama", "Thriller"), ("Los Angeles",)),
        ("sheet_b_table.pdf", ("Horror", "Comedy"), ("New York", "New Jersey")),
        (
            "sheet_c_messy_text.pdf",
            ("Psychological Thriller",),
            ("Atlanta, GA", "Savannah, GA"),
        ),
    ],
)
def test_pdf_models_expose_cleaned_project_data(filename, expected_genres, expected_locations):
    result = extract_document(INPUT / filename)
    assert result.projects
    first = result.projects[0]
    assert tuple(first.genres) == expected_genres
    assert tuple(first.locations or first.shoot_locations) == expected_locations


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
    assert "Wrote 4 project(s)" in capsys.readouterr().out


def test_project_has_empty_cleaned_values_for_missing_and_tbd_fields():
    project = Project.model_validate({"project_title": "Quiet Hours", "start_date": "TBD"})
    assert project.studio is None
    assert project.studio_cleaned is None
    assert project.genres == []
    assert project.locations == []
    assert project.start_date_cleaned is None
    assert project.start_date_flag == "Date is marked TBD."
