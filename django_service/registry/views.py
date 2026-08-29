"""Django APIs for immutable audits and provenance-backed ledger facts."""
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import AUDIT_FIELDS, create_audit_record, serialize_audit
from .models import Filing, IngestionRecord, LegalEntity, OwnershipInterest, QueryAudit


class AuditCreateSerializer(serializers.Serializer):
    """Validates the exact audit payload accepted from the FastAPI service."""
    request_id = serializers.UUIDField()
    question = serializers.CharField(allow_blank=False, trim_whitespace=False)
    as_of = serializers.DateField(allow_null=True)
    generated_cypher = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        trim_whitespace=False,
    )
    cypher_executed = serializers.BooleanField()
    model_name = serializers.CharField(max_length=100)
    model_digest = serializers.CharField(max_length=128)
    schema_version = serializers.CharField(max_length=64)
    resolved_entities = serializers.ListField(child=serializers.DictField())
    citations = serializers.ListField(child=serializers.DictField())
    outcome = serializers.ChoiceField(choices=QueryAudit.Outcome.values)
    final_response = serializers.JSONField()
    failure_reason = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
    )


class InternalAuditCreateView(APIView):
    """Accepts append-only audit writes from the local FastAPI service."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # Reject shape changes so audit replay always receives complete known fields.
        if request.query_params:
            return Response(
                {"detail": "Unknown query parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(request.data, dict) or set(request.data) != AUDIT_FIELDS:
            return Response(
                {
                    "detail": {
                        "unexpected_fields": sorted(set(request.data) - AUDIT_FIELDS)
                        if isinstance(request.data, dict)
                        else [],
                        "missing_fields": sorted(AUDIT_FIELDS - set(request.data))
                        if isinstance(request.data, dict)
                        else sorted(AUDIT_FIELDS),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AuditCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            audit = create_audit_record(serializer.validated_data)
        except ValidationError as exc:
            return Response(
                {"detail": exc.message_dict if hasattr(exc, "message_dict") else exc.messages},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(serialize_audit(audit), status=status.HTTP_201_CREATED)


class AuditDetailView(APIView):
    """Return one immutable audit record for review or evaluation."""
    authentication_classes = []
    permission_classes = []

    def get(self, request, request_id):
        """Read a stored audit row without allowing alternate query parameters."""
        if request.query_params:
            return Response(
                {"detail": "Unknown query parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audit = get_object_or_404(QueryAudit, request_id=request_id)
        return Response(serialize_audit(audit))


class LedgerEntityView(APIView):
    """Return authoritative entity, filing, ownership, and source provenance facts."""
    authentication_classes = []
    permission_classes = []

    def get(self, request, entity_uid):
        """Collect the requested entity's ledger facts from PostgreSQL only."""
        if request.query_params:
            return Response(
                {"detail": "Unknown query parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entity = get_object_or_404(LegalEntity, entity_uid=entity_uid)
        # Ledger responses include provenance because PostgreSQL is the source of truth.
        interests = list(
            OwnershipInterest.objects.filter(
                Q(held_entity=entity) | Q(holder_entity=entity)
            )
            .select_related(
                "holder_person",
                "holder_entity",
                "held_entity",
                "filing",
                "provenance",
            )
            .order_by("valid_from", "pk")
        )
        filing_ids = {interest.filing_id for interest in interests if interest.filing_id}
        filings = Filing.objects.filter(
            Q(asserts_about=entity) | Q(filing_uid__in=filing_ids)
        ).order_by("filed_on", "filing_uid")

        return Response(
            {
                "entity": {
                    "entity_uid": entity.entity_uid,
                    "legal_name": entity.legal_name,
                    "legal_name_ar": entity.legal_name_ar,
                    "jurisdiction": entity.jurisdiction,
                    "registration_no": entity.registration_no,
                    "incorporation_date": entity.incorporation_date.isoformat(),
                    "status": entity.status,
                    "status_as_of": entity.status_as_of.isoformat(),
                    "provenance": _record_provenance(
                        IngestionRecord.objects.filter(
                            source_file="entities.jsonl",
                            raw_payload__entity_uid=entity.entity_uid,
                        ).first()
                    ),
                },
                "filings": [_serialize_filing(filing) for filing in filings],
                "ownership_interests": [
                    _serialize_interest(interest) for interest in interests
                ],
            }
        )


def _serialize_filing(filing):
    """Serialize one filing with the source line that produced it."""
    provenance = IngestionRecord.objects.filter(
        source_file="filings.jsonl",
        raw_payload__filing_uid=filing.filing_uid,
    ).first()
    return {
        "filing_uid": filing.filing_uid,
        "filing_type": filing.filing_type,
        "filed_on": filing.filed_on.isoformat(),
        "source_registry": filing.source_registry,
        "asserts_about": filing.asserts_about_id,
        "supersedes": filing.supersedes_id,
        "provenance": _record_provenance(provenance),
    }


def _serialize_interest(interest):
    """Serialize one ownership assertion without changing its bps or dates."""
    holder_type = "NaturalPerson" if interest.holder_person_id else "LegalEntity"
    holder_uid = interest.holder_person_id or interest.holder_entity_id
    return {
        "relationship": "HOLDS_INTEREST_IN",
        "holder_type": holder_type,
        "holder_uid": holder_uid,
        "held_entity_uid": interest.held_entity_id,
        "bps": interest.bps,
        "valid_from": interest.valid_from.isoformat(),
        "valid_to": interest.valid_to.isoformat() if interest.valid_to else None,
        "filing_uid": interest.filing_id,
        "provenance": _record_provenance(interest.provenance),
    }


def _record_provenance(record):
    """Return source-file and line-number context for a ledger record."""
    if record is None:
        return None
    return {
        "source_file": record.source_file,
        "line_number": record.line_number,
        "ingestion_status": record.status,
        "reason": record.reason,
    }
