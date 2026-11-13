"""Conservative, explicit normalization rules for extracted listing values."""

from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Literal

DatePrecision = Literal["day", "part_of_month", "month", "season", "quarter", "unknown"]

GENRES = (
    "Action",
    "Adventure",
    "Animation",
    "Biography",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "History",
    "Horror",
    "Mystery",
    "Musical",
    "Romance",
    "Science Fiction",
    "Sports",
    "Thriller",
    "War",
    "Western",
    "Young Adult",
)

_GENRE_BY_KEY = {genre.casefold(): genre for genre in GENRES}
_GENRE_ALIASES = {
    "sci-fi": ("Science Fiction",),
    "science-fiction": ("Science Fiction",),
    "ya": ("Young Adult",),
    "dramedy": ("Comedy", "Drama"),
    "romantic comedy": ("Romance", "Comedy"),
}
_GENRE_QUALIFIER = re.compile(r"\s*\([^()]*\)\s*$")
_GENRE_SEPARATOR = re.compile(r"\s*(?:/|,|;|\+|&)\s*|\s+and\s+", re.IGNORECASE)
_STUDIO_SEPARATOR = re.compile(r"\s*(?:/|;|\+)\s*")

_LOCATION_ALIASES = {
    "la": "Los Angeles",
    "l.a.": "Los Angeles",
    "ny": "New York",
    "nyc": "New York",
    "nj": "New Jersey",
}
_LOCATION_SEPARATOR = re.compile(r"/|;|\band\b|\bor\b", re.IGNORECASE)
_LOCATION_ALTERNATIVE_SEPARATOR = re.compile(r",|/|;|\band\b|\bor\b", re.IGNORECASE)
_TENTATIVE_LOCATION = re.compile(r"\b(?:likely|tbd)\b", re.IGNORECASE)
_TENTATIVE_DATE = re.compile(r"^\s*(?:prob(?:ably)?\.?|tent(?:ative(?:ly)?)?\.?)\s*", re.IGNORECASE)
_TITLE_SMALL_WORDS = {"a", "an", "and", "in", "of", "the", "to"}
_MONTHS = {name.casefold(): number for number, name in enumerate(calendar.month_name) if name}
_MONTHS.update(
    {name.casefold(): number for number, name in enumerate(calendar.month_abbr) if name}
)
_SEASONS = {"spring": 3, "summer": 6, "fall": 9, "autumn": 9, "winter": 12}


def clean_text(value: str | None) -> str | None:
    """Collapse layout whitespace without changing the source wording."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def normalize_project_title(value: str | None) -> str | None:
    """Title-case cleaned project titles while lower-casing interior small words."""
    cleaned = clean_text(value)
    if cleaned is None:
        return None

    words = cleaned.title().split()
    for index in range(1, len(words)):
        words[index] = re.sub(
            r"[A-Za-z]+",
            lambda match: (
                match.group().lower()
                if match.group().casefold() in _TITLE_SMALL_WORDS
                else match.group()
            ),
            words[index],
        )
    return re.sub(r"\bTv\b", "TV", " ".join(words))


def normalize_role_name(value: str | None) -> str | None:
    """Clean layout whitespace and title-case names printed entirely in capitals."""
    cleaned = clean_text(value)
    if cleaned and any(character.isalpha() for character in cleaned) and cleaned.isupper():
        return cleaned.title()
    return cleaned


def _genre_values(value: str) -> tuple[str, ...]:
    folded = value.casefold()
    if folded in _GENRE_ALIASES:
        return _GENRE_ALIASES[folded]
    canonical = _GENRE_BY_KEY.get(folded)
    if canonical:
        return (canonical,)

    without_qualifier = _GENRE_QUALIFIER.sub("", value).strip()
    if without_qualifier != value:
        canonical = _GENRE_BY_KEY.get(without_qualifier.casefold())
        if canonical:
            return (canonical,)

    terms = value.split()
    parsed: list[str] = []
    position = 0
    ordered_genres = sorted(GENRES, key=lambda genre: len(genre.split()), reverse=True)
    while position < len(terms):
        match = next(
            (
                genre
                for genre in ordered_genres
                if [word.casefold() for word in terms[position : position + len(genre.split())]]
                == genre.casefold().split()
            ),
            None,
        )
        if match is None:
            break
        parsed.append(match)
        position += len(match.split())
    if position == len(terms) and len(parsed) > 1:
        return tuple(parsed)
    suffix = next(
        (
            genre
            for genre in sorted(GENRES, key=len, reverse=True)
            if folded.endswith(f" {genre.casefold()}")
        ),
        None,
    )
    if suffix:
        return (suffix,)
    return (value,)


def normalize_genres(value: str | None) -> list[str]:
    """Map known genre labels to a fixed vocabulary and retain unknown terms."""
    cleaned = clean_text(value)
    if cleaned is None:
        return []

    pieces = _GENRE_SEPARATOR.split(cleaned)
    result: list[str] = []
    for piece in pieces:
        term = clean_text(piece)
        if term is None:
            continue

        # Split an unspaced hyphen only when both sides are known genres.
        hyphen_parts = re.fullmatch(r"([A-Za-z ]+)-([A-Za-z ]+)", term)
        if hyphen_parts and all(
            part.strip().casefold() in _GENRE_BY_KEY for part in hyphen_parts.groups()
        ):
            values = tuple(_GENRE_BY_KEY[part.strip().casefold()] for part in hyphen_parts.groups())
        else:
            values = _genre_values(term)

        for genre in values:
            if genre.casefold() not in {existing.casefold() for existing in result}:
                result.append(genre)
    return result


def _normalize_place(value: str) -> str:
    cleaned = (clean_text(value) or "").split(",", maxsplit=1)[0].strip()
    return _LOCATION_ALIASES.get(cleaned.casefold(), cleaned)


def _split_location_text(value: str, split_commas: bool) -> list[str]:
    separator = _LOCATION_ALTERNATIVE_SEPARATOR if split_commas else _LOCATION_SEPARATOR
    pieces: list[str] = []
    start = 0
    depth = 0
    for match in separator.finditer(value):
        depth += value[start:match.start()].count("(") - value[start:match.start()].count(")")
        if depth == 0:
            pieces.append(value[start:match.start()])
            start = match.end()
    pieces.append(value[start:])
    return pieces


def normalize_locations(value: str | None) -> tuple[list[str], str | None]:
    """Return one cleaned name per listed place and flag tentative wording."""
    cleaned = clean_text(value)
    if cleaned is None:
        return [], None

    tentative = bool(_TENTATIVE_LOCATION.search(cleaned))
    if tentative:
        alternatives = re.search(r"\(([^()]*)\)\s*$", cleaned)
        if alternatives:
            cleaned = alternatives.group(1)
        cleaned = _TENTATIVE_LOCATION.sub("", cleaned)
        cleaned = cleaned.strip(" \t,;:.-()")

    if not cleaned:
        return [], "Location is marked TBD or otherwise tentative." if tentative else None

    parenthetical = re.fullmatch(r"\s*(.*?)\s*\(([^()]*)\)\s*", cleaned)
    if parenthetical and _LOCATION_ALTERNATIVE_SEPARATOR.search(parenthetical.group(2)):
        outer, inner = parenthetical.groups()
        pieces = _split_location_text(outer, split_commas=False)
        pieces.extend(_LOCATION_ALTERNATIVE_SEPARATOR.split(inner))
    elif tentative:
        pieces = _LOCATION_ALTERNATIVE_SEPARATOR.split(cleaned)
    else:
        pieces = _split_location_text(cleaned, split_commas=False)

    locations: list[str] = []
    for piece in pieces:
        place = _normalize_place(piece.strip(" \t,;:."))
        if place and place.casefold() not in {item.casefold() for item in locations}:
            locations.append(place)

    flag = "Location is tentative; listed place names are retained." if tentative else None
    return locations, flag


def normalize_studios(value: str | None) -> list[str]:
    """Split a printed studio field into the listed company names."""
    cleaned = clean_text(value)
    if cleaned is None:
        return []
    return [
        studio
        for piece in _STUDIO_SEPARATOR.split(cleaned)
        if (studio := clean_text(piece)) is not None
    ]


def _parse_single_date(value: str) -> tuple[date | None, DatePrecision, str | None]:
    iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", value)
    if iso_match:
        try:
            return date(*(int(part) for part in iso_match.groups())), "day", None
        except ValueError:
            return None, "unknown", "Date is not a valid calendar date."

    numeric_match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})", value)
    if numeric_match:
        month, day, year = numeric_match.groups()
        try:
            full_year = int(year) if len(year) == 4 else 2000 + int(year)
            return date(full_year, int(month), int(day)), "day", None
        except ValueError:
            return None, "unknown", "Date is not a valid calendar date."

    quarter_match = re.fullmatch(r"Q([1-4])\s+(\d{4})", value, re.IGNORECASE)
    if quarter_match:
        quarter, year = (int(part) for part in quarter_match.groups())
        return date(year, (quarter - 1) * 3 + 1, 1), "quarter", None

    season_match = re.fullmatch(
        r"(?:(?:early|mid|late)[ -]+)?(spring|summer|fall|autumn|winter)\s+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if season_match:
        season, year = season_match.groups()
        month = _SEASONS[season.casefold()]
        return date(int(year), month, 1), "season", None

    month_match = re.fullmatch(
        r"(?:(early|mid|late)[ -]+)?([A-Za-z]+)[,. ]+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if month_match:
        part, month_name, year = month_match.groups()
        month = _MONTHS.get(month_name.casefold().rstrip("."))
        if month:
            day = {"early": 5, "mid": 15, "late": 25}.get(
                part.casefold() if part else "", 1
            )
            precision: DatePrecision = "part_of_month" if part else "month"
            return date(int(year), month, day), precision, None

    day_match = re.fullmatch(
        r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if day_match:
        month_name, day, year = day_match.groups()
        month = _MONTHS.get(month_name.casefold().rstrip("."))
        if month:
            try:
                return date(int(year), month, int(day)), "day", None
            except ValueError:
                return None, "unknown", "Date is not a valid calendar date."

    return None, "unknown", "Date format is ambiguous or unsupported."


def normalize_start_date(
    value: str | None,
) -> tuple[date | None, DatePrecision, str | None]:
    """Normalize recognized dates without discarding the printed date or its precision."""
    cleaned = clean_text(value)
    if cleaned is None:
        return None, "unknown", None
    if re.fullmatch(r"TBD|to be determined", cleaned, re.IGNORECASE):
        return None, "unknown", "Date is marked TBD."

    tentative_match = _TENTATIVE_DATE.match(cleaned)
    tentative = tentative_match is not None
    candidate = _TENTATIVE_DATE.sub("", cleaned, count=1).strip(" .:-")

    quarter_range = re.match(
        r"^(Q[1-4]\s+\d{4})\s*/\s*Q[1-4]\s+\d{4}$",
        candidate,
        re.IGNORECASE,
    )
    range_match = re.search(r"\s+(?:to|through|until)\s+", candidate, re.IGNORECASE)
    if quarter_range:
        candidate = quarter_range.group(1)
    elif range_match:
        candidate = candidate[: range_match.start()].strip()

    parsed, precision, flag = _parse_single_date(candidate)
    if parsed is None:
        return None, "unknown", flag

    if tentative:
        flag = "Date is tentative."
    return parsed, precision, flag


def normalize_role_type(value: str | None) -> str | None:
    """Standardize known role labels while preserving unknown labels."""
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    known = {
        "lead": "Lead",
        "supporting": "Supporting",
        "supporting lead": "Supporting Lead",
        "recurring": "Recurring",
        "co-star": "Co-Star",
        "small": "Small",
        "guest star": "Guest Star",
        "day player": "Day Player",
        "series regular": "Series Regular",
    }
    return known.get(cleaned.casefold(), cleaned)


def normalize_gender(value: str | None) -> str | None:
    """Standardize common gender labels while retaining unfamiliar values."""
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    known = {
        "female": "Female",
        "male": "Male",
        "any": "Any",
        "any gender": "Any",
    }
    return known.get(cleaned.casefold(), cleaned)
