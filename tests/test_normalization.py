from datetime import date

import pytest

from src.normalization import (
    GENRES,
    clean_text,
    normalize_gender,
    normalize_genres,
    normalize_locations,
    normalize_role_type,
    normalize_start_date,
)


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("Drama/Thriller", ["Drama", "Thriller"]),
        ("Dramedy", ["Comedy", "Drama"]),
        ("Rom-Com", ["Romance", "Comedy"]),
        ("Action-Adventure", ["Action", "Adventure"]),
        ("Horror-Comedy", ["Horror", "Comedy"]),
        ("Sci-Fi / YA", ["Science Fiction", "Young Adult"]),
        ("Crime Drama", ["Crime", "Drama"]),
        ("Comedy/Period", ["Comedy", "Period"]),
        ("Psychological Thriller", ["Thriller"]),
        ("Drama (Character Oriented)", ["Drama"]),
        (None, []),
        ("  ", []),
    ],
)
def test_genre_rules(printed, expected):
    assert normalize_genres(printed) == expected


def test_genres_use_a_fixed_canonical_vocabulary():
    assert "Action" in GENRES
    assert "Science Fiction" in GENRES
    assert "Young Adult" in GENRES
    assert len(GENRES) == len(set(GENRES))


def test_text_cleaning_collapses_layout_whitespace_without_losing_words():
    assert clean_text("  A  small-town\n story ") == "A small-town story"
    assert clean_text(None) is None


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("LEAD", "Lead"),
        ("supporting lead", "Supporting Lead"),
        ("CO-STAR", "Co-Star"),
        ("series regular", "Series Regular"),
        ("Unlisted Role", "Unlisted Role"),
        (None, None),
    ],
)
def test_role_type_rules(printed, expected):
    assert normalize_role_type(printed) == expected


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("female", "Female"),
        ("MALE", "Male"),
        ("any gender", "Any"),
        ("nonbinary", "nonbinary"),
        (None, None),
    ],
)
def test_gender_rules(printed, expected):
    assert normalize_gender(printed) == expected


@pytest.mark.parametrize(
    ("printed", "expected", "flag"),
    [
        ("LA", ["Los Angeles"], None),
        ("Los Angeles, CA", ["Los Angeles"], None),
        ("NY/NJ", ["New York", "New Jersey"], None),
        ("NY", ["New York"], None),
        ("NYC", ["New York"], None),
        ("Toronto, ON", ["Toronto"], None),
        ("Atlanta, GA", ["Atlanta"], None),
        ("Likely NYC", ["New York"], "Location is tentative; listed place names are retained."),
        (
            "TBD (LA, NY or Vancouver)",
            ["Los Angeles", "New York", "Vancouver"],
            "Location is tentative; listed place names are retained.",
        ),
        ("TBD", [], "Location is marked TBD or otherwise tentative."),
        ("Calgary, Alberta, Canada", ["Calgary"], None),
        (
            "Eastern Europe (Prague or Budapest)",
            ["Eastern Europe", "Prague", "Budapest"],
            None,
        ),
        (None, [], None),
    ],
)
def test_location_rules(printed, expected, flag):
    assert normalize_locations(printed) == (expected, flag)


@pytest.mark.parametrize(
    ("printed", "expected", "precision", "flag"),
    [
        ("Spring 2026", date(2026, 3, 1), "season", None),
        ("Winter 2026", date(2026, 12, 1), "season", None),
        ("2/1/2026", date(2026, 2, 1), "day", None),
        ("July 13, 2026", date(2026, 7, 13), "day", None),
        ("Q1 2027", date(2027, 1, 1), "quarter", None),
        ("Mid-August 2026", date(2026, 8, 15), "part_of_month", None),
        ("Late August 2026", date(2026, 8, 25), "part_of_month", None),
        ("10/24/25", date(2025, 10, 24), "day", None),
        ("Tent. Summer 2026", date(2026, 6, 1), "season", "Date is tentative."),
        (
            "Prob. Nov 2025 to Feb 2026",
            date(2025, 11, 1),
            "month",
            "Date is tentative.",
        ),
        ("Q4 2025/Q1 2026", date(2025, 10, 1), "quarter", None),
        ("TBD", None, "unknown", "Date is marked TBD."),
        ("Not sure yet", None, "unknown", "Date format is ambiguous or unsupported."),
        (None, None, "unknown", None),
    ],
)
def test_start_date_rules(printed, expected, precision, flag):
    assert normalize_start_date(printed) == (expected, precision, flag)


def test_invalid_calendar_date_is_not_normalized():
    assert normalize_start_date("2/30/2026") == (
        None,
        "unknown",
        "Date is not a valid calendar date.",
    )
