"""Validated output models retaining printed text beside cleaned values."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.normalization import (
    DatePrecision,
    clean_text,
    normalize_gender,
    normalize_genres,
    normalize_locations,
    normalize_project_title,
    normalize_role_name,
    normalize_role_type,
    normalize_start_date,
    normalize_studios,
)


class Role(BaseModel):
    """A parsed role with both source text and normalized values."""

    model_config = ConfigDict(extra="forbid")

    role_name: str
    role_name_cleaned: str
    role_type: str | None = None
    role_type_cleaned: str | None = None
    gender: str | None = None
    gender_cleaned: str | None = None
    age: str | None = None
    age_cleaned: str | None = None
    notes: str | None = None
    notes_cleaned: str | None = None
    role_flag: str | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_cleaned_values(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        for field, normalize in (
            ("role_name", normalize_role_name),
            ("role_type", normalize_role_type),
            ("gender", normalize_gender),
            ("age", clean_text),
            ("notes", clean_text),
        ):
            if field in data and (data[field] is None or isinstance(data[field], str)):
                data[f"{field}_cleaned"] = normalize(data[field])
        role_name = data.get("role_name")
        if isinstance(role_name, str) and role_name.strip().casefold() == "tbd role":
            data["role_flag"] = "Role is marked TBD."
        return data


class Project(BaseModel):
    """A parsed project with source values, cleaned values, and its roles."""

    model_config = ConfigDict(extra="forbid")

    project_title: str
    project_title_cleaned: str
    title_alias: str | None = None
    project_type: str | None = None
    project_type_cleaned: str | None = None
    studio: str | None = None
    studio_cleaned: str | None = None
    studios: list[str] = Field(default_factory=list)
    genre: str | None = None
    genres: list[str] = Field(default_factory=list)
    location: str | None = None
    locations: list[str] = Field(default_factory=list)
    location_flag: str | None = None
    start_date: str | None = None
    start_date_cleaned: date | None = None
    start_date_precision: DatePrecision = "unknown"
    start_date_flag: str | None = None
    status: str | None = None
    status_cleaned: str | None = None
    synopsis: str | None = None
    synopsis_cleaned: str | None = None
    network: str | None = None
    network_cleaned: str | None = None
    shoot_location: str | None = None
    shoot_locations: list[str] = Field(default_factory=list)
    shoot_location_flag: str | None = None
    roles: list[Role] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def populate_cleaned_values(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        for field in ("project_title", "project_type", "studio", "status", "synopsis", "network"):
            if field in data and (data[field] is None or isinstance(data[field], str)):
                normalize = normalize_project_title if field == "project_title" else clean_text
                data[f"{field}_cleaned"] = normalize(data[field])
        if "studio" in data and (data["studio"] is None or isinstance(data["studio"], str)):
            data["studios"] = normalize_studios(data["studio"])
        if "genre" in data and (data["genre"] is None or isinstance(data["genre"], str)):
            data["genres"] = normalize_genres(data["genre"])
        if "location" in data and (data["location"] is None or isinstance(data["location"], str)):
            data["locations"], data["location_flag"] = normalize_locations(data["location"])
        if "start_date" in data and (
            data["start_date"] is None or isinstance(data["start_date"], str)
        ):
            (
                data["start_date_cleaned"],
                data["start_date_precision"],
                data["start_date_flag"],
            ) = normalize_start_date(data["start_date"])
        if "shoot_location" in data and (
            data["shoot_location"] is None or isinstance(data["shoot_location"], str)
        ):
            data["shoot_locations"], data["shoot_location_flag"] = normalize_locations(
                data["shoot_location"]
            )
        return data


class PDFWord(BaseModel):
    """A positioned word extracted from a PDF page."""

    model_config = ConfigDict(extra="forbid")

    text: str
    x0: float
    x1: float
    top: float
    bottom: float


class PDFPage(BaseModel):
    """Full extracted text and positioned text elements for one PDF page."""

    model_config = ConfigDict(extra="forbid")

    page_number: int
    width: float
    height: float
    text: str
    words: list[PDFWord]


class ExtractionResult(BaseModel):
    """JSON document containing extracted pages and parsed projects."""

    model_config = ConfigDict(extra="forbid")

    projects: list[Project]
    pages: list[PDFPage] = Field(default_factory=list)
