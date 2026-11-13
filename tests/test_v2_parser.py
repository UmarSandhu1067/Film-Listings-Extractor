from datetime import date
from pathlib import Path

from src.pdf_reader import read_pdf
from src.v2.cleaning import normalize_genres, normalize_locations, normalize_start_date
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
    assert normalize_start_date("Sept 2026") == (
        date(2026, 9, 1),
        "month",
        None,
    )
