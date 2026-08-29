"""Normalize the supported HOLDS_INTEREST_IN ownership records into PostgreSQL."""
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError

from .models import (
    Filing,
    IngestionRecord,
    LegalEntity,
    NaturalPerson,
    OwnershipInterest,
)


# Marks ownership payloads that are structurally unsafe to normalize.
class OwnershipDataError(ValueError):
    pass


# Marks ownership payloads whose referenced registry rows do not yet exist.
class OwnershipReferenceError(ValueError):
    pass


# Converts one supported ownership payload into an idempotent normalized row.
def normalize_ownership(
    payload: dict[str, Any],
    provenance: IngestionRecord,
) -> None:
    # bps is stored as an integer: 10,000 bps represents 100 percent.
    holder_uid = _required_string(payload, "holder_uid")
    held_uid = _required_string(payload, "held_uid")
    bps = _required_integer(payload, "bps")
    valid_from = _required_date(payload, "valid_from")
    valid_to = _optional_date(payload, "valid_to")
    filing_uid = _optional_string(payload, "filing_uid")

    # Ownership can start at a person or entity, but always ends at a LegalEntity.
    holder_person = None
    holder_entity = None
    if holder_uid.startswith("NP-"):
        holder_person = _get_person(holder_uid)
    elif holder_uid.startswith("LE-"):
        holder_entity = _get_entity(holder_uid, "holder_uid")
    else:
        raise OwnershipDataError(
            "holder_uid must identify a NaturalPerson or LegalEntity"
        )

    held_entity = _get_entity(held_uid, "held_uid")
    filing = _get_filing(filing_uid) if filing_uid is not None else None

    interest = OwnershipInterest.objects.filter(provenance=provenance).first()
    if interest is None:
        interest = OwnershipInterest(provenance=provenance)

    # valid_to=None means this assertion remains currently in force.
    interest.holder_person = holder_person
    interest.holder_entity = holder_entity
    interest.held_entity = held_entity
    interest.bps = bps
    interest.valid_from = valid_from
    interest.valid_to = valid_to
    interest.filing = filing

    try:
        interest.full_clean()
    except ValidationError as exc:
        raise OwnershipDataError(str(exc)) from exc
    interest.save()


# Reads a required ownership identifier or date string without altering it.
def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise OwnershipDataError(f"{field_name} must be a non-empty string")
    return value


# Accepts a nullable ownership string while rejecting empty or non-string values.
def _optional_string(payload: dict[str, Any], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise OwnershipDataError(f"{field_name} must be null or a non-empty string")
    return value


# Requires a genuine integer so booleans cannot be stored as ownership amounts.
def _required_integer(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise OwnershipDataError(f"{field_name} must be an integer")
    return value


# Parses a required ownership date using only the supported ISO representation.
def _required_date(payload: dict[str, Any], field_name: str) -> date:
    value = _required_string(payload, field_name)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OwnershipDataError(f"{field_name} must use YYYY-MM-DD") from exc


# Preserves null effective-date bounds and parses non-null bounds as ISO dates.
def _optional_date(payload: dict[str, Any], field_name: str) -> date | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise OwnershipDataError(f"{field_name} must be null or use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OwnershipDataError(
            f"{field_name} must be null or use YYYY-MM-DD"
        ) from exc


# Resolves a person holder and distinguishes a missing reference from bad data.
def _get_person(person_uid: str) -> NaturalPerson:
    try:
        return NaturalPerson.objects.get(person_uid=person_uid)
    except NaturalPerson.DoesNotExist as exc:
        raise OwnershipReferenceError(
            f"holder_uid references missing NaturalPerson {person_uid}"
        ) from exc


# Resolves an entity reference while retaining the source field in any error.
def _get_entity(entity_uid: str, field_name: str) -> LegalEntity:
    try:
        return LegalEntity.objects.get(entity_uid=entity_uid)
    except LegalEntity.DoesNotExist as exc:
        raise OwnershipReferenceError(
            f"{field_name} references missing LegalEntity {entity_uid}"
        ) from exc


# Resolves optional filing provenance before an ownership row is saved.
def _get_filing(filing_uid: str) -> Filing:
    try:
        return Filing.objects.get(filing_uid=filing_uid)
    except Filing.DoesNotExist as exc:
        raise OwnershipReferenceError(
            f"filing_uid references missing Filing {filing_uid}"
        ) from exc
