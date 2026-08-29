"""Create and replay Django-owned immutable audit records for FastAPI requests."""
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import QueryAudit, SchemaRegistryState


AUDIT_FIELDS = {
    "request_id",
    "question",
    "as_of",
    "generated_cypher",
    "cypher_executed",
    "model_name",
    "model_digest",
    "schema_version",
    "resolved_entities",
    "citations",
    "outcome",
    "final_response",
    "failure_reason",
}


def create_audit_record(validated_data: dict[str, Any]) -> QueryAudit:
    """Validate one complete FastAPI outcome before inserting its audit row."""
    unexpected = set(validated_data) - AUDIT_FIELDS
    missing = AUDIT_FIELDS - set(validated_data)
    if unexpected or missing:
        raise ValidationError(
            {
                "unexpected_fields": sorted(unexpected),
                "missing_fields": sorted(missing),
            }
        )

    # Audit rows record the schema version that governed the original request.
    schema_state = SchemaRegistryState.objects.get(pk=1)
    if validated_data["schema_version"] != schema_state.version:
        raise ValidationError(
            {
                "schema_version": (
                    f"Expected version {schema_state.version!r}, received "
                    f"{validated_data['schema_version']!r}"
                )
            }
        )

    with transaction.atomic():
        for field_name in ("resolved_entities", "citations"):
            value = validated_data[field_name]
            if not isinstance(value, list) or not all(
                isinstance(item, dict) for item in value
            ):
                raise ValidationError(
                    {field_name: "Must be a list of objects."}
                )

        audit = QueryAudit(**validated_data)
        audit.full_clean(exclude=["resolved_entities", "citations"])
        audit.save(force_insert=True)

    return audit


def serialize_audit(audit: QueryAudit) -> dict[str, Any]:
    """Return the stored audit row in the public audit API shape."""
    return {
        "request_id": str(audit.request_id),
        "question": audit.question,
        "as_of": audit.as_of.isoformat() if audit.as_of else None,
        "generated_cypher": audit.generated_cypher,
        "cypher_executed": audit.cypher_executed,
        "model_name": audit.model_name,
        "model_digest": audit.model_digest,
        "schema_version": audit.schema_version,
        "resolved_entities": audit.resolved_entities,
        "citations": audit.citations,
        "outcome": audit.outcome,
        "final_response": audit.final_response,
        "failure_reason": audit.failure_reason,
        "created_at": audit.created_at.isoformat(),
    }


def replay_audit_record(audit: QueryAudit) -> dict[str, Any]:
    """Reconstruct the original response context without re-running the model or graph."""
    return {
        "request_id": str(audit.request_id),
        "request": {
            "question": audit.question,
            "as_of": audit.as_of.isoformat() if audit.as_of else None,
        },
        "generated_cypher": audit.generated_cypher,
        "cypher_executed": audit.cypher_executed,
        "model": {
            "name": audit.model_name,
            "digest": audit.model_digest,
        },
        "schema_version": audit.schema_version,
        "resolved_entities": audit.resolved_entities,
        "citations": audit.citations,
        "outcome": audit.outcome,
        "failure_reason": audit.failure_reason,
        "stored_response_body": audit.final_response,
    }
