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
    normalize_role_type,
    normalize_start_date,
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

    @model_validator(mode="before")
    @classmethod
    def populate_cleaned_values(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        data["role_name_cleaned"] = clean_text(data.get("role_name"))
        data["role_type_cleaned"] = normalize_role_type(data.get("role_type"))
        data["gender_cleaned"] = normalize_gender(data.get("gender"))
        data["age_cleaned"] = clean_text(data.get("age"))
        data["notes_cleaned"] = clean_text(data.get("notes"))
        return data


class Project(BaseModel):
    """A parsed project with source values, cleaned values, and its roles."""

    model_config = ConfigDict(extra="forbid")

    project_title: str
    project_title_cleaned: str
    project_type: str | None = None
    project_type_cleaned: str | None = None
    studio: str | None = None
    studio_cleaned: str | None = None
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
            data[f"{field}_cleaned"] = clean_text(data.get(field))
        data["genres"] = normalize_genres(data.get("genre"))
        data["locations"], data["location_flag"] = normalize_locations(data.get("location"))
        data["start_date_cleaned"], data["start_date_precision"], data["start_date_flag"] = (
            normalize_start_date(data.get("start_date"))
        )
        data["shoot_locations"], data["shoot_location_flag"] = normalize_locations(
            data.get("shoot_location")
        )
        return data


class ExtractionResult(BaseModel):
    """JSON document containing extracted projects."""

    model_config = ConfigDict(extra="forbid")

    projects: list[Project]
