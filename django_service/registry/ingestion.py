"""Load JSONL seed records into PostgreSQL with complete line-level provenance."""
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Filing, IngestionRecord, LegalEntity, NaturalPerson
from .ownership import (
    OwnershipDataError,
    OwnershipReferenceError,
    normalize_ownership,
)


RECORD_TYPES = {
    "asset_control.jsonl": "CONTROLS_ASSET",
    "assets.jsonl": "AssetUnit",
    "entities.jsonl": "LegalEntity",
    "filing_assertions.jsonl": "ASSERTS_ABOUT",
    "filings.jsonl": "Filing",
    "fractionalisation.jsonl": "FRACTIONALISED_AS",
    "instruments.jsonl": "Instrument",
    "interests.jsonl": "HOLDS_INTEREST_IN",
    "persons.jsonl": "NaturalPerson",
    "pledges.jsonl": "PLEDGED_TO",
    "unit_holdings.jsonl": "HOLDS_UNITS",
}

NORMALIZATION_ORDER = {
    "entities.jsonl": 0,
    "persons.jsonl": 1,
    "filings.jsonl": 2,
    "interests.jsonl": 3,
}


# Marks malformed supported records that must remain visible as rejected input.
class RejectedRecord(ValueError):
    pass


# Marks validly shaped records that cannot resolve required foreign keys.
class QuarantinedRecord(ValueError):
    pass


# Loads every JSONL source deterministically and returns per-file and total counts.
def ingest_seed(source: str | Path) -> dict[str, Any]:
    source_directory = Path(source)
    if not source_directory.exists():
        raise FileNotFoundError(f"Seed source does not exist: {source_directory}")
    if not source_directory.is_dir():
        raise NotADirectoryError(
            f"Seed source is not a directory: {source_directory}"
        )

    source_files = sorted(
        source_directory.glob("*.jsonl"),
        key=lambda path: (NORMALIZATION_ORDER.get(path.name, 4), path.name),
    )

    file_summaries: dict[str, dict[str, Any]] = {}
    for source_file in source_files:
        file_summaries[source_file.name] = _ingest_file(source_file)

    total = _new_counts()
    for file_summary in file_summaries.values():
        for key in (
            "records_read",
            "accepted",
            "coerced",
            "quarantined",
            "rejected",
        ):
            total[key] += file_summary[key]
    _finish_counts(total)

    return {"files": file_summaries, "total": total}


# Accounts for every physical line in one source file, including invalid input.
def _ingest_file(source_file: Path) -> dict[str, Any]:
    counts = _new_counts()
    with source_file.open("rb") as lines:
        for line_number, raw_line in enumerate(lines, start=1):
            counts["records_read"] += 1
            status, reason = _ingest_line(source_file.name, line_number, raw_line)
            counts[status] += 1
            if reason:
                counts["reasons"].append(
                    {
                        "line_number": line_number,
                        "status": status,
                        "reason": reason,
                    }
                )

    _finish_counts(counts)
    return counts


# Reuses existing provenance or parses and classifies one new source line.
def _ingest_line(
    source_file: str,
    line_number: int,
    raw_line: bytes,
) -> tuple[str, str]:
    existing = IngestionRecord.objects.filter(
        source_file=source_file,
        line_number=line_number,
    ).first()
    if existing is not None:
        return existing.status, existing.reason

    record_type = RECORD_TYPES.get(source_file, Path(source_file).stem)
    try:
        text = raw_line.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError:
        raw_text = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        reason = "line is not valid UTF-8"
        _save_problem_record(
            source_file,
            line_number,
            record_type,
            raw_text,
            IngestionRecord.Status.REJECTED,
            reason,
        )
        return IngestionRecord.Status.REJECTED, reason

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        reason = f"invalid JSON: {exc.msg}"
        _save_problem_record(
            source_file,
            line_number,
            record_type,
            text,
            IngestionRecord.Status.REJECTED,
            reason,
        )
        return IngestionRecord.Status.REJECTED, reason

    if not isinstance(payload, dict):
        reason = "JSON record must be an object"
        _save_problem_record(
            source_file,
            line_number,
            record_type,
            payload,
            IngestionRecord.Status.REJECTED,
            reason,
        )
        return IngestionRecord.Status.REJECTED, reason

    with transaction.atomic():
        # Create the ledger row first so accepted and failed input remain auditable.
        ingestion_record = IngestionRecord.objects.create(
            source_file=source_file,
            line_number=line_number,
            record_type=record_type,
            raw_payload=payload,
            status=IngestionRecord.Status.ACCEPTED,
            reason="",
        )

        try:
            # Only the supported ownership slice is normalized into business tables.
            coercions = _normalize_record(source_file, payload, ingestion_record)
        except (RejectedRecord, OwnershipDataError) as exc:
            ingestion_record.status = IngestionRecord.Status.REJECTED
            ingestion_record.reason = str(exc)
        except (QuarantinedRecord, OwnershipReferenceError) as exc:
            ingestion_record.status = IngestionRecord.Status.QUARANTINED
            ingestion_record.reason = str(exc)
        else:
            if coercions:
                ingestion_record.status = IngestionRecord.Status.COERCED
                ingestion_record.reason = "; ".join(coercions)

        ingestion_record.save(update_fields=["status", "reason"])

    return ingestion_record.status, ingestion_record.reason


# Routes only the four supported source files into this phase's business models.
def _normalize_record(
    source_file: str,
    payload: dict[str, Any],
    ingestion_record: IngestionRecord,
) -> list[str]:
    if source_file == "entities.jsonl":
        return _normalize_entity(payload)
    if source_file == "persons.jsonl":
        _normalize_person(payload)
    elif source_file == "filings.jsonl":
        _normalize_filing(payload)
    elif source_file == "interests.jsonl":
        normalize_ownership(payload, ingestion_record)
    return []


# Saves schema-supported entity fields and reports any narrow date coercions.
def _normalize_entity(payload: dict[str, Any]) -> list[str]:
    entity_uid = _required_string(payload, "entity_uid")
    incorporation_date, incorporation_reason = _entity_date(
        payload,
        "incorporation_date",
    )
    status_as_of, status_reason = _entity_date(payload, "status_as_of")

    entity = LegalEntity.objects.filter(entity_uid=entity_uid).first()
    if entity is None:
        entity = LegalEntity(entity_uid=entity_uid)
    entity.legal_name = _required_string(payload, "legal_name")
    entity.legal_name_ar = _optional_string(payload, "legal_name_ar")
    entity.jurisdiction = _required_string(payload, "jurisdiction")
    entity.registration_no = _required_string(payload, "registration_no")
    entity.incorporation_date = incorporation_date
    entity.status = _required_string(payload, "status")
    entity.status_as_of = status_as_of
    _validate_and_save(entity)

    return [
        reason
        for reason in (incorporation_reason, status_reason)
        if reason is not None
    ]


# Saves only the NaturalPerson fields allowed by the authoritative registry.
def _normalize_person(payload: dict[str, Any]) -> None:
    person_uid = _required_string(payload, "person_uid")
    person = NaturalPerson.objects.filter(person_uid=person_uid).first()
    if person is None:
        person = NaturalPerson(person_uid=person_uid)
    person.full_name = _required_string(payload, "full_name")
    person.full_name_ar = _optional_string(payload, "full_name_ar")
    person.nationality = _required_string(payload, "nationality")
    person.dob_year = _required_integer(payload, "dob_year")
    _validate_and_save(person)


# Saves a filing only after its entity and optional prior filing can be resolved.
def _normalize_filing(payload: dict[str, Any]) -> None:
    filing_uid = _required_string(payload, "filing_uid")
    asserts_about_uid = _required_string(payload, "asserts_about")
    supersedes_uid = _optional_string(payload, "supersedes")

    try:
        asserts_about = LegalEntity.objects.get(entity_uid=asserts_about_uid)
    except LegalEntity.DoesNotExist as exc:
        raise QuarantinedRecord(
            f"asserts_about references missing LegalEntity {asserts_about_uid}"
        ) from exc

    supersedes = None
    if supersedes_uid is not None:
        try:
            supersedes = Filing.objects.get(filing_uid=supersedes_uid)
        except Filing.DoesNotExist as exc:
            raise QuarantinedRecord(
                f"supersedes references missing Filing {supersedes_uid}"
            ) from exc

    filing = Filing.objects.filter(filing_uid=filing_uid).first()
    if filing is None:
        filing = Filing(filing_uid=filing_uid)
    filing.filing_type = _required_string(payload, "filing_type")
    filing.filed_on = _iso_date(payload, "filed_on")
    filing.source_registry = _required_string(payload, "source_registry")
    filing.asserts_about = asserts_about
    filing.supersedes = supersedes
    _validate_and_save(filing)


# Persists malformed input so rejection never removes a physical source line.
def _save_problem_record(
    source_file: str,
    line_number: int,
    record_type: str,
    raw_payload: Any,
    status: str,
    reason: str,
) -> None:
    IngestionRecord.objects.create(
        source_file=source_file,
        line_number=line_number,
        record_type=record_type,
        raw_payload=raw_payload,
        status=status,
        reason=reason,
    )


# Reads a required source string without stripping or normalizing its contents.
def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise RejectedRecord(f"{field_name} must be a non-empty string")
    return value


# Preserves null source strings while rejecting empty or incorrectly typed values.
def _optional_string(payload: dict[str, Any], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise RejectedRecord(f"{field_name} must be null or a non-empty string")
    return value


# Requires an integer source value while excluding Python booleans.
def _required_integer(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RejectedRecord(f"{field_name} must be an integer")
    return value


# Parses fields that have no fixture-supported non-ISO representation.
def _iso_date(payload: dict[str, Any], field_name: str) -> date:
    value = _required_string(payload, field_name)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RejectedRecord(f"{field_name} must use YYYY-MM-DD") from exc


# Allows the single fixture-backed DD/MM/YYYY entity-date coercion path.
def _entity_date(
    payload: dict[str, Any],
    field_name: str,
) -> tuple[date, str | None]:
    value = _required_string(payload, field_name)
    try:
        return date.fromisoformat(value), None
    except ValueError:
        pass

    try:
        parsed = datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as exc:
        raise RejectedRecord(
            f"{field_name} must use YYYY-MM-DD or DD/MM/YYYY"
        ) from exc
    reason = f"{field_name} coerced from {value!r} to {parsed.isoformat()!r}"
    return parsed, reason


# Applies Django model validation before writing a normalized registry row.
def _validate_and_save(instance: Any) -> None:
    try:
        instance.full_clean()
    except ValidationError as exc:
        raise RejectedRecord(str(exc)) from exc
    instance.save()


# Creates an independent counter set for one file or the overall result.
def _new_counts() -> dict[str, Any]:
    return {
        "records_read": 0,
        "accepted": 0,
        "coerced": 0,
        "quarantined": 0,
        "rejected": 0,
        "reasons": [],
    }


# Calculates the assessment identity without double-counting problem rows.
def _finish_counts(counts: dict[str, Any]) -> None:
    # Quarantine and rejection rows live in IngestionRecord but are separate terms
    # in the assessment identity, so only accepted and coerced count as ledger rows.
    counts["records_in_ledger"] = counts["accepted"] + counts["coerced"]
    counts["reconciled"] = counts["records_read"] == (
        counts["records_in_ledger"]
        + counts["quarantined"]
        + counts["rejected"]
    )
