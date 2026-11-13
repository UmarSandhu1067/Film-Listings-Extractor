"""Validated V2 records; source values remain beside their cleaned forms."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.v2.cleaning import (
    DatePrecision,
    clean_text,
    normalize_genres,
    normalize_locations,
    normalize_networks,
    normalize_start_date,
    normalize_studios,
    normalize_title,
)


class V2Role(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_name: str
    role_name_cleaned: str | None = None
    role_type: str | None = None
    role_type_cleaned: str | None = None
    status: str | None = None
    cast_name: str | None = None
    cast_person_key: str | None = None
    description: str | None = None
    description_cleaned: str | None = None
    role_flag: str | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_cleaned_values(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        name = data.get("role_name")
        if isinstance(name, str):
            data["role_name_cleaned"] = name.title() if name.isupper() else name
        for field in ("role_type", "description"):
            if field in data and isinstance(data[field], str):
                data[f"{field}_cleaned"] = clean_text(data[field])
        return data


class V2Credit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code_printed: str | None = None
    code: str | None = None
    role: str | None = None
    kind: Literal["person", "company"]
    name: str = Field(min_length=1)
    name_cleaned: str | None = None
    person_key: str | None = None
    company: str | None = None
    note: str | None = None
    phone: str | None = None
    phone_cleaned: str | None = None
    email: str | None = None
    flag: str | None = None


class V2Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_title: str
    project_title_cleaned: str
    title_alias: str | None = None
    aliases: list[str] = Field(default_factory=list)
    section: str | None = None
    network: str | None = None
    network_cleaned: str | None = None
    networks: list[str] = Field(default_factory=list)
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
    roles: list[V2Role] = Field(default_factory=list)
    credits: list[V2Credit] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def populate_cleaned_values(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        title = data.get("project_title")
        if isinstance(title, str):
            data["project_title_cleaned"] = normalize_title(title)
        for field in ("network", "studio", "status", "synopsis"):
            if field in data and isinstance(data[field], str):
                data[f"{field}_cleaned"] = clean_text(data[field])
        if isinstance(data.get("network"), str):
            data["networks"] = normalize_networks(data["network"])
        if isinstance(data.get("studio"), str):
            data["studios"] = normalize_studios(data["studio"])
        if isinstance(data.get("genre"), str):
            data["genres"] = normalize_genres(data["genre"])
        if isinstance(data.get("location"), str):
            data["locations"], data["location_flag"] = normalize_locations(data["location"])
        if isinstance(data.get("start_date"), str):
            (
                data["start_date_cleaned"],
                data["start_date_precision"],
                data["start_date_flag"],
            ) = normalize_start_date(data["start_date"])
        return data
