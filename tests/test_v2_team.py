from pathlib import Path

from src.pdf_reader import read_pdf
from src.v2.entities import merge_people_companies
from src.v2.layout import iter_sheet_d_lines
from src.v2.models import V2Project
from src.v2.parser import parse_sheet_d
from src.v2.team import parse_team_lines

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHEET_D = PROJECT_ROOT / "input" / "sheet_d_two_column_grid.pdf"


def test_combined_unknown_placeholder_and_wrapped_names():
    credits = parse_team_lines(
        [
            "EP/W JANE SAMPLE [pilot], HELEN",
            "ABARA",
            "XYZ UNKNOWN PERSON",
            "CD TBA",
        ]
    )

    jane_credits = [credit for credit in credits if credit["name_cleaned"] == "Jane Sample"]
    assert [(credit["code_printed"], credit["code"]) for credit in jane_credits] == [
        ("EP/W", "EP"),
        ("EP/W", "W"),
    ]
    assert all(credit["note"] == "pilot" for credit in jane_credits)
    helen = next(credit for credit in credits if credit["name_cleaned"] == "Helen Abara")
    assert helen["name"] == "HELEN ABARA"
    unknown = next(credit for credit in credits if credit["name"] == "UNKNOWN PERSON")
    assert unknown["role"] is None
    assert unknown["flag"] == "Unknown credit code: XYZ."
    assert all(credit["name"].casefold() not in {"tba", "tbd"} for credit in credits)


def test_company_links_contacts_and_phone_formats():
    credits = parse_team_lines(
        [
            "CD Hollis & Wren Casting",
            "Jo Hollis (212) 555-0100 jo@EXAMPLE.test",
            "Sam Wren 310.555.0177",
            "EP Ravi Kessler +44 20 7946 0958",
        ]
    )

    company = next(credit for credit in credits if credit["kind"] == "company")
    jo = next(credit for credit in credits if credit["name"] == "Jo Hollis")
    sam = next(credit for credit in credits if credit["name"] == "Sam Wren")
    ravi = next(credit for credit in credits if credit["name"] == "Ravi Kessler")
    assert company["name"] == "Hollis & Wren Casting"
    assert jo["company"] == company["name"]
    assert sam["company"] == company["name"]
    assert (jo["phone"], jo["phone_cleaned"], jo["email"]) == (
        "(212) 555-0100",
        "+12125550100",
        "jo@example.test",
    )
    assert sam["phone_cleaned"] == "+13105550177"
    assert ravi["phone_cleaned"] == "+442079460958"


def test_sheet_d_team_counts_and_merged_people_companies():
    raw_projects = parse_sheet_d(iter_sheet_d_lines(read_pdf(SHEET_D)))
    projects = [V2Project.model_validate(project) for project in raw_projects]
    people, companies = merge_people_companies(
        [project.model_dump(mode="python") for project in projects]
    )

    assert len(projects) == 8
    assert sum(len(project.credits) for project in projects) == 37
    assert len(people) == 17
    assert len(companies) == 2
    jo = next(person for person in people if person["person_key"] == "jo-hollis")
    assert jo["phones"] == ["+13105550142", "+442079460958"]
    assert jo["companies"] == ["Hollis & Wren Casting"]
    assert jo["projects"] == ["EMBER STREET", "the understudies"]
    marisol = next(person for person in people if person["person_key"] == "marisol-vega")
    assert marisol["phones"] == ["+13105550164"]
    assert marisol["emails"] == ["marisol@vegacasting.example"]
    andre = next(person for person in people if person["person_key"] == "andre-mbeki")
    assert andre["projects"] == ["EMBER STREET"]
