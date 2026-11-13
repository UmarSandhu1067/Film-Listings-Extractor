"""V2-only cleaning rules that preserve source values separately."""

from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Literal

DatePrecision = Literal[
    "day",
    "month",
    "part_of_month",
    "quarter",
    "season",
    "year",
    "unknown",
]

_SMALL_TITLE_WORDS = {"a", "an", "and", "in", "of", "the", "to"}
_GENRES = (
    "Action",
    "Adventure",
    "Comedy",
    "Crime",
    "Drama",
    "Family",
    "Fantasy",
    "Horror",
    "Mystery",
    "Musical",
    "Romance",
    "Science Fiction",
    "Thriller",
    "War",
    "Western",
)
_GENRE_ALIASES = {
    "dramedy": ("Comedy", "Drama"),
    "rom-com": ("Romance", "Comedy"),
    "romantic comedy": ("Romance", "Comedy"),
    "sci-fi": ("Science Fiction",),
}
_MONTHS = {
    name.casefold(): number
    for number, name in enumerate(calendar.month_name)
    if name
}
_MONTHS.update(
    {name.casefold(): number for number, name in enumerate(calendar.month_abbr) if name}
)
_MONTHS["sept"] = 9


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def normalize_title(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    words = cleaned.title().split()
    for index in range(1, len(words)):
        words[index] = re.sub(
            r"[A-Za-z]+",
            lambda match: (
                match.group().lower()
                if match.group().casefold() in _SMALL_TITLE_WORDS
                else match.group()
            ),
            words[index],
        )
    return re.sub(r"\bTv\b", "TV", " ".join(words))


def normalize_name(value: str) -> str:
    cleaned = clean_text(value) or ""
    if cleaned.isupper():
        return cleaned.title()
    return cleaned


def normalize_entity_key(value: str) -> str:
    cleaned = clean_text(value) or ""
    return re.sub(r"[\W_]+", "-", cleaned.casefold()).strip("-")


def clean_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return f"+{digits}" if value.lstrip().startswith("+") else f"+1{digits}"


def normalize_email(value: str) -> str:
    return value.strip().lower()


def _known_genre(term: str) -> tuple[str, ...] | None:
    folded = term.casefold().strip()
    if folded in _GENRE_ALIASES:
        return _GENRE_ALIASES[folded]
    return next(
        ((genre,) for genre in _GENRES if genre.casefold() == folded),
        None,
    )


def normalize_genres(value: str | None) -> list[str]:
    cleaned = clean_text(value)
    if cleaned is None:
        return []

    pieces = re.split(r"\s*(?:/|,|;|\+|&)\s*|\s+and\s+", cleaned, flags=re.IGNORECASE)
    result: list[str] = []
    for piece in pieces:
        term = clean_text(piece)
        if term is None:
            continue
        mapped = _known_genre(term)
        if mapped is None:
            words = term.split()
            found: list[str] = []
            index = 0
            while index < len(words):
                match = next(
                    (
                        genre
                        for genre in sorted(_GENRES, key=len, reverse=True)
                        if [word.casefold() for word in words[index:index + len(genre.split())]]
                        == genre.casefold().split()
                    ),
                    None,
                )
                if match is None:
                    found = []
                    break
                found.append(match)
                index += len(match.split())
            mapped = tuple(found) if index == len(words) and len(found) > 1 else None
        values = mapped if mapped is not None else (term,)
        for genre in values:
            if genre.casefold() not in {item.casefold() for item in result}:
                result.append(genre)
    return result


def normalize_networks(value: str | None) -> list[str]:
    cleaned = clean_text(value)
    if cleaned is None:
        return []
    return [part.strip() for part in re.split(r"\s*(?:/|;|\|)\s*", cleaned) if part.strip()]


def normalize_studios(value: str | None) -> list[str]:
    cleaned = clean_text(value)
    if cleaned is None:
        return []
    return [part.strip() for part in re.split(r"\s*(?:/|;|\+)\s*", cleaned) if part.strip()]


def normalize_locations(value: str | None) -> tuple[list[str], str | None]:
    cleaned = clean_text(value)
    if cleaned is None:
        return [], None

    tentative = bool(re.search(r"\b(?:likely|tbd)\b", cleaned, re.IGNORECASE))
    alternatives = re.search(r"\(([^()]*)\)\s*$", cleaned)
    if tentative and alternatives:
        candidate = alternatives.group(1)
        separator = r"\s*(?:,|/|;|&|\band\b|\bor\b)\s*"
    else:
        candidate = re.sub(r"^\s*(?:likely|tbd)\b", "", cleaned, flags=re.IGNORECASE)
        candidate = candidate.strip(" \t,;:.-()")
        separator = r"\s*(?:/|;|&|\band\b|\bor\b)\s*"

    places: list[str] = []
    for part in re.split(separator, candidate, flags=re.IGNORECASE):
        place = clean_text(part)
        if place is None:
            continue
        place = place.split(",", maxsplit=1)[0].strip()
        if place and place.casefold() not in {item.casefold() for item in places}:
            places.append(place)

    flag = "Location is tentative; listed place names are retained." if tentative else None
    return places, flag


def normalize_start_date(
    value: str | None,
) -> tuple[date | None, DatePrecision, str | None]:
    cleaned = clean_text(value)
    if cleaned is None:
        return None, "unknown", None
    if re.fullmatch(r"TBD|to be determined", cleaned, re.IGNORECASE):
        return None, "unknown", "Date is marked TBD."

    tentative = bool(re.match(r"^(?:tent\.?|prob\.?)\s*", cleaned, re.IGNORECASE))
    candidate = re.sub(r"^(?:tent\.?|prob\.?)\s*", "", cleaned, flags=re.IGNORECASE)
    parsed: date
    precision: DatePrecision
    year = re.fullmatch(r"\d{4}", candidate)
    if year:
        try:
            parsed, precision = date(int(candidate), 1, 1), "year"
        except ValueError:
            return None, "unknown", "Date is not a valid calendar date."
    else:
        quarter = re.fullmatch(r"Q([1-4])\s+(\d{4})", candidate, re.IGNORECASE)
        month = re.fullmatch(
            r"(?:(early|mid|late)[ -]+)?([A-Za-z]+)[,. ]+(\d{4})",
            candidate,
            re.IGNORECASE,
        )
        season = re.fullmatch(
            r"(?:spring|summer|fall|autumn|winter)\s+(\d{4})",
            candidate,
            re.IGNORECASE,
        )
        if quarter:
            quarter_number, quarter_year = (int(value) for value in quarter.groups())
            try:
                parsed, precision = (
                    date(quarter_year, (quarter_number - 1) * 3 + 1, 1),
                    "quarter",
                )
            except ValueError:
                return None, "unknown", "Date is not a valid calendar date."
        elif month and (month_value := _MONTHS.get(month.group(2).casefold().rstrip("."))):
            part = month.group(1)
            try:
                day = {"early": 5, "mid": 15, "late": 25}.get(part.casefold() if part else "", 1)
                parsed, precision = (
                    date(int(month.group(3)), month_value, day),
                    "part_of_month" if part else "month",
                )
            except ValueError:
                return None, "unknown", "Date is not a valid calendar date."
        elif season:
            season_month = {
                "spring": 3,
                "summer": 6,
                "fall": 9,
                "autumn": 9,
                "winter": 12,
            }[candidate.split()[0].casefold()]
            try:
                parsed, precision = date(int(season.group(1)), season_month, 1), "season"
            except ValueError:
                return None, "unknown", "Date is not a valid calendar date."
        else:
            numeric = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})", candidate)
            if numeric:
                numeric_month, numeric_day, year_value = numeric.groups()
                full_year = int(year_value) if len(year_value) == 4 else 2000 + int(year_value)
                try:
                    parsed, precision = (
                        date(full_year, int(numeric_month), int(numeric_day)),
                        "day",
                    )
                except ValueError:
                    return None, "unknown", "Date is not a valid calendar date."
            else:
                return None, "unknown", "Date format is ambiguous or unsupported."

    flag = "Date is tentative." if tentative else None
    return parsed, precision, flag
