import json
from pathlib import Path

from src.v2.extractor import extract_document
from src.v2.main import cli

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHEET_D = PROJECT_ROOT / "input" / "sheet_d_two_column_grid.pdf"


def test_v2_document_matches_sheet_d_counts_and_retains_source_values():
    document = extract_document(SHEET_D)

    assert len(document.projects) == 8
    assert sum(len(project.roles) for project in document.projects) == 22
    assert sum(len(project.credits) for project in document.projects) == 37
    assert len(document.people) == 17
    assert len(document.companies) == 2
    low_tide = next(project for project in document.projects if project.project_title == "LOW TIDE")
    assert low_tide.title_alias == "(fka Harbor Lights)"
    assert low_tide.aliases == ["Harbor Lights"]
    assert low_tide.network == "Streamwave / Coastline+"
    assert low_tide.networks == ["Streamwave", "Coastline+"]
    assert low_tide.location == "Halifax, NS & St. John's, NL"
    assert low_tide.locations == ["Halifax", "St. John's"]
    assert low_tide.start_date_cleaned is not None
    assert low_tide.start_date_cleaned.isoformat() == "2027-03-15"
    assert low_tide.start_date_precision == "part_of_month"


def test_v2_cli_writes_complete_document(tmp_path, capsys):
    output = tmp_path / "sheet_d.json"

    code = cli([str(SHEET_D), "--out", str(output)])

    document = json.loads(output.read_text(encoding="utf-8"))
    assert code == 0
    assert len(document["projects"]) == 8
    assert len(document["people"]) == 17
    assert len(document["companies"]) == 2
    assert "Wrote 8 project(s)" in capsys.readouterr().out


def test_v2_cli_reports_missing_input_without_traceback(tmp_path, capsys):
    missing = tmp_path / "missing.pdf"

    code = cli([str(missing), "--out", str(tmp_path / "out.json")])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == f"Error: input PDF not found: {missing}\n"
