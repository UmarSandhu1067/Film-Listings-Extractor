"""Merge V2 people and companies from project credits and cast roles."""

from __future__ import annotations

from typing import Any

from src.v2.cleaning import normalize_entity_key, normalize_name


def _append_unique(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def merge_people_companies(
    projects: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    people: dict[str, dict[str, Any]] = {}
    companies: dict[str, dict[str, Any]] = {}

    for project in projects:
        project_title = project["project_title"]
        for credit in project.get("credits", []):
            name = credit["name_cleaned"]
            if credit["kind"] == "company":
                key = credit["company_key"] or normalize_entity_key(name)
                company = companies.setdefault(
                    key,
                    {
                        "company_key": key,
                        "name": name,
                        "phones": [],
                        "projects": [],
                    },
                )
                _append_unique(company["projects"], project_title)
                _append_unique(company["phones"], credit.get("phone_cleaned"))
                continue

            key = credit["person_key"] or normalize_entity_key(name)
            person = people.setdefault(
                key,
                {
                    "person_key": key,
                    "name": name,
                    "phones": [],
                    "emails": [],
                    "companies": [],
                    "projects": [],
                },
            )
            _append_unique(person["projects"], project_title)
            _append_unique(person["phones"], credit.get("phone_cleaned"))
            _append_unique(person["emails"], credit.get("email"))
            company_name = credit.get("company")
            if company_name:
                _append_unique(person["companies"], company_name)
                company_key = normalize_entity_key(company_name)
                company = companies.setdefault(
                    company_key,
                    {
                        "company_key": company_key,
                        "name": normalize_name(company_name),
                        "phones": [],
                        "projects": [],
                    },
                )
                _append_unique(company["projects"], project_title)

        for role in project.get("roles", []):
            cast_name = role.get("cast_name")
            if not cast_name:
                continue
            key = normalize_entity_key(cast_name)
            person = people.setdefault(
                key,
                {
                    "person_key": key,
                    "name": normalize_name(cast_name),
                    "phones": [],
                    "emails": [],
                    "companies": [],
                    "projects": [],
                },
            )
            _append_unique(person["projects"], project_title)
            role["cast_person_key"] = key

    return list(people.values()), list(companies.values())
