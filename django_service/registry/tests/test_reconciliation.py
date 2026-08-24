from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from registry.models import (
    Filing,
    IngestionRecord,
    LegalEntity,
    NaturalPerson,
    OwnershipInterest,
)
from registry.reconciliation import reconcile_projection


GRAPH_ENVIRONMENT = {
    "GRAPH_DB_URI": "bolt://neo4j:7687",
    "GRAPH_DB_USER": "neo4j",
    "GRAPH_DB_PASSWORD": "password",
}


# Describes read-only reconciliation of the ownership projection.
class ProjectionReconciliationTests(TestCase):
    def setUp(self):
        self.held_entity = self._entity("LE-HELD", "Held Company")
        self.holder_entity = self._entity("LE-HOLDER", "Holder Company")
        self.holder_person = NaturalPerson.objects.create(
            person_uid="NP-HOLDER",
            full_name="Person Holder",
            full_name_ar=None,
            nationality="JO",
            dob_year=1980,
        )
        filing = Filing.objects.create(
            filing_uid="FL-001",
            filing_type="Ownership filing",
            filed_on=date(2024, 1, 2),
            source_registry="Companies Registry",
            asserts_about=self.held_entity,
        )
        OwnershipInterest.objects.create(
            holder_person=self.holder_person,
            held_entity=self.held_entity,
            bps=5100,
            valid_from=date(2024, 1, 1),
            filing=filing,
            provenance=self._provenance(1),
        )
        OwnershipInterest.objects.create(
            holder_entity=self.holder_entity,
            held_entity=self.held_entity,
            bps=4900,
            valid_from=date(2023, 1, 1),
            valid_to=date(2023, 12, 31),
            provenance=self._provenance(2),
        )

    @patch.dict("os.environ", GRAPH_ENVIRONMENT)
    @patch("registry.reconciliation.GraphDatabase.driver")
    def test_exact_projection_reconciles(self, driver_factory):
        self._neo4j_results(driver_factory)

        result = reconcile_projection()

        self.assertTrue(result["reconciled"])
        self.assertTrue(result["LegalEntity"]["matches"])
        self.assertTrue(result["NaturalPerson"]["matches"])
        self.assertTrue(result["HOLDS_INTEREST_IN"]["matches"])
        self.assertEqual(result["HOLDS_INTEREST_IN"]["expected"], 2)
        self.assertEqual(result["HOLDS_INTEREST_IN"]["actual"], 2)

    @patch.dict("os.environ", GRAPH_ENVIRONMENT)
    @patch("registry.reconciliation.GraphDatabase.driver")
    def test_missing_entity_and_extra_entity_are_detected(self, driver_factory):
        self._neo4j_results(
            driver_factory,
            entity_uids=["LE-HELD", "LE-EXTRA"],
        )

        result = reconcile_projection()

        self.assertFalse(result["reconciled"])
        self.assertFalse(result["LegalEntity"]["matches"])
        self.assertEqual(result["LegalEntity"]["expected"], 2)
        self.assertEqual(result["LegalEntity"]["actual"], 2)
        self.assertEqual(
            result["LegalEntity"]["missing_uids"],
            ["LE-HOLDER"],
        )
        self.assertEqual(
            result["LegalEntity"]["extra_uids"],
            ["LE-EXTRA"],
        )

    @patch.dict("os.environ", GRAPH_ENVIRONMENT)
    @patch("registry.reconciliation.GraphDatabase.driver")
    def test_ownership_property_drift_fails_with_equal_counts(
        self,
        driver_factory,
    ):
        ownership_rows = self._ownership_rows()
        ownership_rows[0]["bps"] = 5000
        self._neo4j_results(
            driver_factory,
            ownership_rows=ownership_rows,
        )

        result = reconcile_projection()

        relationship_result = result["HOLDS_INTEREST_IN"]
        self.assertFalse(result["reconciled"])
        self.assertFalse(relationship_result["matches"])
        self.assertEqual(relationship_result["expected"], 2)
        self.assertEqual(relationship_result["actual"], 2)
        self.assertEqual(len(relationship_result["missing_relationships"]), 1)
        self.assertEqual(len(relationship_result["extra_relationships"]), 1)

    def _neo4j_results(
        self,
        driver_factory,
        entity_uids=None,
        ownership_rows=None,
    ):
        if entity_uids is None:
            entity_uids = ["LE-HELD", "LE-HOLDER"]
        if ownership_rows is None:
            ownership_rows = self._ownership_rows()

        driver = driver_factory.return_value
        session = MagicMock()
        driver.session.return_value.__enter__.return_value = session
        session.run.side_effect = [
            [{"entity_uid": uid} for uid in entity_uids],
            [{"person_uid": "NP-HOLDER"}],
            ownership_rows,
        ]

    def _ownership_rows(self):
        return [
            {
                "holder_type": "NaturalPerson",
                "holder_uid": "NP-HOLDER",
                "held_uid": "LE-HELD",
                "bps": 5100,
                "valid_from": "2024-01-01",
                "valid_to": None,
                "filing_uid": "FL-001",
            },
            {
                "holder_type": "LegalEntity",
                "holder_uid": "LE-HOLDER",
                "held_uid": "LE-HELD",
                "bps": 4900,
                "valid_from": "2023-01-01",
                "valid_to": "2023-12-31",
                "filing_uid": None,
            },
        ]

    def _entity(self, entity_uid, legal_name):
        return LegalEntity.objects.create(
            entity_uid=entity_uid,
            legal_name=legal_name,
            legal_name_ar=None,
            jurisdiction="JO",
            registration_no=f"REG-{entity_uid}",
            incorporation_date=date(2020, 1, 1),
            status="Active",
            status_as_of=date(2026, 1, 31),
        )

    def _provenance(self, line_number):
        return IngestionRecord.objects.create(
            source_file="interests.jsonl",
            line_number=line_number,
            record_type="HOLDS_INTEREST_IN",
            raw_payload={"line": line_number},
            status=IngestionRecord.Status.ACCEPTED,
            reason="",
        )
