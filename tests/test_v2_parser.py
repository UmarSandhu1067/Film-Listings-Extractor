from datetime import date
from pathlib import Path

from src.main import extract_projects as extract_v1_projects
from src.pdf_reader import read_pdf
from src.v2.cleaning import (
    normalize_genres,
    normalize_locations,
    normalize_start_date,
    normalize_title,
)
from src.v2.layout import iter_sheet_d_lines
from src.v2.models import V2Project
from src.v2.parser import parse_sheet_d

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHEET_D = PROJECT_ROOT / "input" / "sheet_d_two_column_grid.pdf"


def _projects() -> list[dict]:
    return parse_sheet_d(iter_sheet_d_lines(read_pdf(SHEET_D)))


def test_extracts_sheet_d_project_order_fields_and_sections():
    projects = _projects()

    assert [project["project_title"] for project in projects] == [
        "EMBER STREET",
        "THE GLASS MERIDIAN",
        "LOW TIDE",
        "NINE MILE ROAD",
        "SECOND SHIFT",
        "the understudies",
        "PORCH LIGHT",
        "KEYS TO THE VAN",
    ]
    assert [project["section"] for project in projects] == [
        "ONE-HOUR SERIES",
        "ONE-HOUR SERIES",
        "ONE-HOUR SERIES",
        "ONE-HOUR SERIES",
        "HALF-HOUR SERIES",
        "HALF-HOUR SERIES",
        "HALF-HOUR SERIES",
        "HALF-HOUR SERIES",
    ]

    ember, glass, low_tide, _, _, _, porch_light, keys = [
        V2Project.model_validate(project) for project in projects
    ]
    assert ember.network == "Streamwave"
    assert ember.status == "Casting"
    assert ember.synopsis == (
        "An arson investigator returns to the neighborhood she grew up in "
        "when a string of fires follows the route of her old school bus."
    )
    assert glass.location == "TBD (Toronto or Montreal)"
    assert low_tide.aliases == ["Harbor Lights"]
    assert porch_light.start_date == "Tent. May 2027"
    assert keys.start_date_cleaned is not None
    assert keys.start_date_cleaned.isoformat() == "2027-01-01"
    assert keys.start_date_precision == "year"


def test_v2_cleaning_handles_sheet_d_genre_location_and_date_forms():
    assert normalize_title("THE LANTERN KEEPER") == "The Lantern Keeper"
    assert normalize_title("SALT AND IRON") == "Salt and Iron"
    assert normalize_title("the brass whistle") == "The Brass Whistle"
    assert normalize_genres("Rom-Com") == ["Romance", "Comedy"]
    assert normalize_genres("Western / Thriller") == ["Western", "Thriller"]
    assert normalize_locations("Halifax, NS & St. John's, NL")[0] == [
        "Halifax",
        "St. John's",
    ]
    assert normalize_locations("Likely Vancouver, BC") == (
        ["Vancouver"],
        "Location is tentative; listed place names are retained.",
    )
    assert normalize_locations("Likely Toronto, ON") == (
        ["Toronto"],
        "Location is tentative; listed place names are retained.",
    )
    assert normalize_start_date("Sept 2026") == (
        date(2026, 9, 1),
        "month",
        None,
    )
    assert normalize_start_date("Mid-March 2027") == (
        date(2027, 3, 15),
        "part_of_month",
        None,
    )


def test_v1_sheets_remain_12_projects_and_30_roles():
    v1_projects = [
        project
        for filename in (
            "sheet_a_labelled_fields.pdf",
            "sheet_b_table.pdf",
            "sheet_c_messy_text.pdf",
        )
        for project in extract_v1_projects(PROJECT_ROOT / "input" / filename)["projects"]
    ]

    assert len(v1_projects) == 12
    assert sum(len(project["roles"]) for project in v1_projects) == 30


def test_extracts_sheet_d_roles_cast_status_and_descriptions():
    projects = [V2Project.model_validate(project) for project in _projects()]
    roles = [role for project in projects for role in project.roles]
    ember = next(project for project in projects if project.project_title == "EMBER STREET")
    glass = next(project for project in projects if project.project_title == "THE GLASS MERIDIAN")
    low_tide = next(project for project in projects if project.project_title == "LOW TIDE")
    keys = next(project for project in projects if project.project_title == "KEYS TO THE VAN")

    assert len(roles) == 22
    assert len(glass.roles) == 0
    chief = next(role for role in ember.roles if role.role_name == "CHIEF AL BRANDT")
    assert (chief.role_type, chief.status, chief.cast_name, chief.cast_person_key) == (
        "Series Regular",
        "Cast",
        "Andre Mbeki",
        "andre-mbeki",
    )
    captain = next(role for role in low_tide.roles if role.role_name == "CAPTAIN JO MERCER")
    assert captain.status == "OFFER OUT"
    assert captain.description == "Female, 40s. Runs the ferry, hides the ledger."
    tbd_role = next(role for role in keys.roles if role.role_name == "TBD ROLE")
    assert tbd_role.role_flag == "Role is marked TBD."
