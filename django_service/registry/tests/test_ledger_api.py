from datetime import date

from django.test import TestCase

from registry.models import (
    Filing,
    IngestionRecord,
    LegalEntity,
    NaturalPerson,
    OwnershipInterest,
)


class LedgerEntityApiTests(TestCase):
    def setUp(self):
        self.entity = LegalEntity.objects.create(
            entity_uid="LE-001",
            legal_name="Held Company",
            legal_name_ar=None,
            jurisdiction="JO",
            registration_no="JO-001",
            incorporation_date=date(2020, 1, 1),
            status="Active",
            status_as_of=date(2026, 1, 31),
        )
        self.person = NaturalPerson.objects.create(
            person_uid="NP-001",
            full_name="Owner Person",
            full_name_ar=None,
            nationality="JO",
            dob_year=1980,
        )
        self.entity_provenance = IngestionRecord.objects.create(
            source_file="entities.jsonl",
            line_number=1,
            record_type="LegalEntity",
            raw_payload={
                "entity_uid": "LE-001",
                "legal_name": "Held Company",
                "internal_risk_note": "must not leak",
            },
            status=IngestionRecord.Status.ACCEPTED,
            reason="",
        )
        filing = Filing.objects.create(
            filing_uid="FL-001",
            filing_type="Ownership filing",
            filed_on=date(2024, 1, 2),
            source_registry="Registry",
            asserts_about=self.entity,
        )
        IngestionRecord.objects.create(
            source_file="filings.jsonl",
            line_number=1,
            record_type="Filing",
            raw_payload={"filing_uid": "FL-001"},
            status=IngestionRecord.Status.ACCEPTED,
            reason="",
        )
        provenance = IngestionRecord.objects.create(
            source_file="interests.jsonl",
            line_number=4,
            record_type="HOLDS_INTEREST_IN",
            raw_payload={"holder_uid": "NP-001", "held_uid": "LE-001"},
            status=IngestionRecord.Status.ACCEPTED,
            reason="",
        )
        OwnershipInterest.objects.create(
            holder_person=self.person,
            held_entity=self.entity,
            bps=5100,
            valid_from=date(2024, 1, 1),
            filing=filing,
            provenance=provenance,
        )

    def test_ledger_entity_get_returns_normalized_record(self):
        response = self.client.get("/api/v1/ledger/entities/LE-001")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entity"]["entity_uid"], "LE-001")
        self.assertEqual(response.json()["filings"][0]["filing_uid"], "FL-001")

    def test_ledger_ownership_includes_provenance(self):
        response = self.client.get("/api/v1/ledger/entities/LE-001")

        ownership = response.json()["ownership_interests"][0]
        self.assertEqual(ownership["holder_uid"], "NP-001")
        self.assertEqual(ownership["provenance"]["source_file"], "interests.jsonl")
        self.assertEqual(ownership["provenance"]["line_number"], 4)

    def test_ledger_does_not_leak_unsupported_raw_fields(self):
        response = self.client.get("/api/v1/ledger/entities/LE-001")

        self.assertNotIn("raw_payload", response.json()["entity"])
        self.assertNotIn("internal_risk_note", str(response.json()))
