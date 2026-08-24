from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from registry.graph_projection import project_graph
from registry.models import (
    Filing,
    IngestionRecord,
    LegalEntity,
    NaturalPerson,
    OwnershipInterest,
)


# Describes the first ownership-only Neo4j projection slice.
class GraphProjectionTests(TestCase):
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
            valid_to=None,
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

    @patch.dict(
        "os.environ",
        {
            "GRAPH_DB_URI": "bolt://neo4j:7687",
            "GRAPH_DB_USER": "neo4j",
            "GRAPH_DB_PASSWORD": "password",
        },
    )
    @patch("registry.graph_projection.GraphDatabase.driver")
    def test_rebuild_returns_stable_projection_counts(self, driver_factory):
        session = self._session(driver_factory)

        first_counts = project_graph()
        second_counts = project_graph()

        expected_counts = {
            "LegalEntity": 2,
            "NaturalPerson": 1,
            "HOLDS_INTEREST_IN": 2,
        }
        self.assertEqual(first_counts, expected_counts)
        self.assertEqual(second_counts, expected_counts)
        delete_calls = [
            call
            for call in session.run.call_args_list
            if "DETACH DELETE" in call.args[0]
        ]
        self.assertEqual(len(delete_calls), 2)

    @patch.dict(
        "os.environ",
        {
            "GRAPH_DB_URI": "bolt://neo4j:7687",
            "GRAPH_DB_USER": "neo4j",
            "GRAPH_DB_PASSWORD": "password",
        },
    )
    @patch("registry.graph_projection.GraphDatabase.driver")
    def test_person_ownership_maps_to_legal_entity(self, driver_factory):
        session = self._session(driver_factory)

        project_graph()

        call = self._relationship_call(session, "NaturalPerson")
        self.assertEqual(call.kwargs["holder_uid"], "NP-HOLDER")
        self.assertEqual(call.kwargs["held_uid"], "LE-HELD")
        self.assertEqual(call.kwargs["bps"], 5100)
        self.assertEqual(call.kwargs["valid_from"], date(2024, 1, 1))
        self.assertIsNone(call.kwargs["valid_to"])
        self.assertEqual(call.kwargs["filing_uid"], "FL-001")

    @patch.dict(
        "os.environ",
        {
            "GRAPH_DB_URI": "bolt://neo4j:7687",
            "GRAPH_DB_USER": "neo4j",
            "GRAPH_DB_PASSWORD": "password",
        },
    )
    @patch("registry.graph_projection.GraphDatabase.driver")
    def test_entity_ownership_maps_to_legal_entity(self, driver_factory):
        session = self._session(driver_factory)

        project_graph()

        call = self._relationship_call(session, "holder:LegalEntity")
        self.assertEqual(call.kwargs["holder_uid"], "LE-HOLDER")
        self.assertEqual(call.kwargs["held_uid"], "LE-HELD")
        self.assertEqual(call.kwargs["bps"], 4900)
        self.assertEqual(call.kwargs["valid_to"], date(2023, 12, 31))
        self.assertIsNone(call.kwargs["filing_uid"])

    def _session(self, driver_factory):
        driver = driver_factory.return_value
        session = MagicMock()
        driver.session.return_value.__enter__.return_value = session
        return session

    def _relationship_call(self, session, holder_label):
        return next(
            call
            for call in session.run.call_args_list
            if "HOLDS_INTEREST_IN" in call.args[0]
            and holder_label in call.args[0]
        )

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
