import json
from datetime import date
from io import StringIO
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from registry.audit import create_audit_record
from registry.models import QueryAudit


class AuditTests(TestCase):
    def _payload(self, outcome="answered"):
        response = {
            "status": outcome,
            "answer": "Stored response",
            "resolved_entities": [],
            "citations": [],
        }
        return {
            "request_id": uuid4(),
            "question": "Who owns LE-001?",
            "as_of": date(2024, 1, 1),
            "generated_cypher": "MATCH (n:LegalEntity) RETURN n LIMIT 1",
            "cypher_executed": outcome == "answered",
            "model_name": "qwen3:4b",
            "model_digest": "digest",
            "schema_version": "watheeq-graph-1.0.0",
            "resolved_entities": [],
            "citations": [],
            "outcome": outcome,
            "final_response": response,
            "failure_reason": "",
        }

    def test_audit_creation(self):
        audit = create_audit_record(self._payload())

        self.assertEqual(QueryAudit.objects.count(), 1)
        self.assertEqual(audit.question, "Who owns LE-001?")

    def test_internal_endpoint_creates_audit(self):
        payload = self._payload()
        payload["request_id"] = str(payload["request_id"])
        payload["as_of"] = payload["as_of"].isoformat()

        response = self.client.post(
            "/internal/audit",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(QueryAudit.objects.filter(request_id=payload["request_id"]).exists())

    def test_audit_schema_version_must_match_version_in_force(self):
        payload = self._payload()
        payload["schema_version"] = "wrong-version"

        with self.assertRaises(ValidationError):
            create_audit_record(payload)

        self.assertFalse(QueryAudit.objects.exists())

    def test_audit_cannot_be_updated_through_model(self):
        audit = create_audit_record(self._payload())
        audit.failure_reason = "changed"

        with self.assertRaises(ValidationError):
            audit.save()

    def test_audit_cannot_be_deleted_through_model(self):
        audit = create_audit_record(self._payload())

        with self.assertRaises(ValidationError):
            audit.delete()

    def test_audit_queryset_cannot_bulk_update_or_delete(self):
        audit = create_audit_record(self._payload())

        with self.assertRaises(ValidationError):
            QueryAudit.objects.filter(pk=audit.pk).update(failure_reason="changed")
        with self.assertRaises(ValidationError):
            QueryAudit.objects.filter(pk=audit.pk).delete()

    def test_public_audit_get_returns_complete_record(self):
        audit = create_audit_record(self._payload())

        response = self.client.get(f"/api/v1/audit/{audit.request_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["request_id"], str(audit.request_id))
        self.assertEqual(response.json()["final_response"], audit.final_response)

    def test_internal_audit_create_rejects_schema_drift(self):
        payload = self._payload()
        payload["request_id"] = str(payload["request_id"])
        payload["as_of"] = payload["as_of"].isoformat()
        payload["schema_version"] = "wrong-version"

        response = self.client.post(
            "/internal/audit",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(QueryAudit.objects.exists())

    def test_internal_audit_create_rejects_unknown_fields(self):
        payload = self._payload()
        payload["request_id"] = str(payload["request_id"])
        payload["as_of"] = payload["as_of"].isoformat()
        payload["debug"] = True

        response = self.client.post(
            "/internal/audit",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(QueryAudit.objects.exists())

    def test_replay_reconstructs_success_from_row_alone(self):
        self._assert_replay("answered")

    def test_replay_reconstructs_abstention_from_row_alone(self):
        self._assert_replay("abstained")

    def test_replay_reconstructs_refusal_from_row_alone(self):
        self._assert_replay("refused")

    def _assert_replay(self, outcome):
        payload = self._payload(outcome)
        audit = create_audit_record(payload)
        output = StringIO()

        call_command("replay_audit", request_id=str(audit.request_id), stdout=output)

        replay = json.loads(output.getvalue())
        self.assertEqual(replay["outcome"], outcome)
        self.assertEqual(replay["stored_response_body"], payload["final_response"])
        self.assertEqual(replay["request"]["question"], payload["question"])
