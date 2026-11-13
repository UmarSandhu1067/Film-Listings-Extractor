"""V2 TEAM block parsing for credits, names, notes, and contact details."""

from __future__ import annotations

import re
from typing import Any

from src.v2.cleaning import (
    clean_phone,
    clean_text,
    normalize_email,
    normalize_entity_key,
    normalize_name,
)

_CODE_ROLES = {
    "EP": "Executive Producer",
    "CEP": "Co-Executive Producer",
    "P": "Producer",
    "D": "Director",
    "W": "Writer",
    "CR": "Creator",
    "CD": "Casting Director",
}
_CODE_LINE_RE = re.compile(r"^([A-Z]{1,3}(?:/[A-Z]{1,3})*)(?:\s+(.*))?$")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+\d[\d\s().-]*\d|\(?\d[\d\s().-]{5,}\d\)?)(?!\w)")
_COMPANY_SUFFIXES = (
    "casting",
    "films",
    "pictures",
    "studios",
    "media",
    "entertainment",
    "house",
)


def _is_company(name: str) -> bool:
    folded = name.casefold().rstrip(" .")
    return any(folded.endswith(suffix) for suffix in _COMPANY_SUFFIXES)


def _is_code_line(text: str) -> tuple[str, str] | None:
    match = _CODE_LINE_RE.fullmatch(text.strip())
    if not match or match.group(1) in {"TBA", "TBD"}:
        return None
    code = match.group(1)
    if (
        code not in _CODE_ROLES
        and not any(part in _CODE_ROLES for part in code.split("/"))
        and "/" not in code
        and len(code) > 3
    ):
        return None
    return code, (match.group(2) or "").strip()


def _split_commas(text: str) -> list[str]:
    result: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(0, depth - 1)
        elif character == "," and depth == 0:
            result.append(text[start:index])
            start = index + 1
    result.append(text[start:])
    return result


def _name_parts(text: str) -> list[tuple[str, str | None]]:
    entries: list[tuple[str, str | None]] = []
    for segment in _split_commas(text):
        notes = [
            (match.group(1) or match.group(2)).strip()
            for match in re.finditer(r"\(([^)]*)\)|\[([^\]]*)\]", segment)
            if (match.group(1) or match.group(2)).strip()
        ]
        name_text = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", segment).strip()
        if not name_text:
            continue
        names = (
            [name_text]
            if _is_company(name_text)
            else [part.strip() for part in re.split(r"\s*&\s*", name_text) if part.strip()]
        )
        note = "; ".join(notes) or None
        for name in names:
            if name.casefold() not in {"tba", "tbd"}:
                entries.append((name, note))
    return entries


def _should_join_name(previous: str, following: str) -> bool:
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", following.strip()):
        return False
    if _PHONE_RE.search(previous) or _EMAIL_RE.search(previous):
        return False
    without_notes = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", previous)
    last_segment = re.split(r"[, &]+", without_notes.strip())[-1]
    return len(last_segment.split()) == 1


def _contacts(text: str) -> tuple[str, list[str], list[str]]:
    phones = [match.group().strip() for match in _PHONE_RE.finditer(text)]
    emails = [match.group().strip() for match in _EMAIL_RE.finditer(text)]
    remainder = _PHONE_RE.sub(" ", text)
    remainder = _EMAIL_RE.sub(" ", remainder)
    return remainder.strip(), phones, emails


def _build_credit(
    name: str,
    note: str | None,
    code_printed: str | None,
    current_company: str | None,
) -> list[dict[str, Any]]:
    cleaned_name = normalize_name(name)
    kind = "company" if _is_company(cleaned_name) else "person"
    codes = code_printed.split("/") if code_printed else [None]
    result: list[dict[str, Any]] = []
    for code in codes:
        role = _CODE_ROLES.get(code or "")
        flag = None
        if code is None:
            flag = "No credit code printed."
        elif role is None:
            flag = f"Unknown credit code: {code}."
        credit: dict[str, Any] = {
            "code_printed": code_printed,
            "code": code,
            "role": role,
            "kind": kind,
            "name": name,
            "name_cleaned": cleaned_name,
            "note": note,
            "company": current_company if kind == "person" else None,
            "flag": flag,
        }
        if kind == "person":
            credit["person_key"] = normalize_entity_key(name)
        else:
            credit["company_key"] = normalize_entity_key(name)
        result.append(credit)
    return result


def parse_team_lines(lines: list[str]) -> list[dict[str, Any]]:
    """Parse one TEAM block, retaining unknown or missing credit codes as flags."""
    credits: list[dict[str, Any]] = []
    current_code_printed: str | None = None
    current_company: str | None = None
    last_credit: dict[str, Any] | None = None
    pending_text: str | None = None
    pending_code: str | None = None

    def attach_contacts(
        records: list[dict[str, Any]],
        phones: list[str],
        emails: list[str],
    ) -> None:
        if not records:
            return
        for record in records:
            if phones:
                record["phone"] = phones[-1]
                record["phone_cleaned"] = clean_phone(phones[-1])
            if emails:
                record["email"] = normalize_email(emails[-1])

    def consume(text: str, code_printed: str | None) -> None:
        nonlocal current_company, last_credit
        remainder, phones, emails = _contacts(text)
        entries = _name_parts(remainder)
        if not entries:
            if last_credit:
                attach_contacts([last_credit], phones, emails)
            return

        for index, (name, note) in enumerate(entries):
            records = _build_credit(name, note, code_printed, current_company)
            if _is_company(name):
                current_company = normalize_name(name)
                for record in records:
                    record["company"] = None
            attach_contacts(records, phones if index == len(entries) - 1 else [], emails if index == len(entries) - 1 else [])
            credits.extend(records)
            if records:
                last_credit = records[-1]

    for raw_line in lines:
        line = clean_text(raw_line) or ""
        if not line:
            continue
        code_line = _is_code_line(line)
        if code_line:
            if pending_text is not None:
                consume(pending_text, pending_code)
                pending_text = None
            current_code_printed, remainder = code_line
            pending_code = current_code_printed
            if remainder:
                pending_text = remainder
            else:
                pending_code = current_code_printed
            continue

        if pending_text is not None and _should_join_name(pending_text, line):
            pending_text = f"{pending_text} {line}"
            continue

        if pending_text is not None:
            consume(pending_text, pending_code)
            pending_text = None

        if pending_code is None:
            pending_code = current_code_printed
        pending_text = line

    if pending_text is not None:
        consume(pending_text, pending_code)
    return credits
