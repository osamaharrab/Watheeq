from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from registry.models import IngestionRecord, LegalEntity, NaturalPerson, OwnershipInterest


# Describes the database invariants required by the registry models.
class RegistryModelTests(TestCase):
    # Creates the minimum parties needed by each isolated ownership test.
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

    # Confirms entity identity comes from entity_uid rather than legal_name.
    def test_duplicate_legal_names_are_allowed(self):
        first = self._entity("LE-DUPLICATE-1", "Duplicate Legal Name")
        second = self._entity("LE-DUPLICATE-2", "Duplicate Legal Name")

        self.assertNotEqual(first.entity_uid, second.entity_uid)
        self.assertEqual(first.legal_name, second.legal_name)

    # Confirms one physical source line cannot create two provenance rows.
    def test_source_file_and_line_number_are_unique_together(self):
        self._provenance(1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self._provenance(1)

    # Confirms the schema-supported person-to-entity ownership shape.
    def test_person_can_hold_an_ownership_interest(self):
        interest = OwnershipInterest.objects.create(
            holder_person=self.holder_person,
            held_entity=self.held_entity,
            bps=5100,
            valid_from=date(2020, 1, 1),
            provenance=self._provenance(2),
        )

        self.assertEqual(interest.holder_person, self.holder_person)
        self.assertIsNone(interest.holder_entity)

    # Confirms the schema-supported entity-to-entity ownership shape.
    def test_entity_can_hold_an_ownership_interest(self):
        interest = OwnershipInterest.objects.create(
            holder_entity=self.holder_entity,
            held_entity=self.held_entity,
            bps=4900,
            valid_from=date(2020, 1, 1),
            provenance=self._provenance(3),
        )

        self.assertEqual(interest.holder_entity, self.holder_entity)
        self.assertIsNone(interest.holder_person)

    # Confirms an ownership row cannot identify both holder types at once.
    def test_ownership_interest_rejects_two_holders(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OwnershipInterest.objects.create(
                holder_person=self.holder_person,
                holder_entity=self.holder_entity,
                held_entity=self.held_entity,
                bps=5000,
                valid_from=date(2020, 1, 1),
                provenance=self._provenance(4),
            )

    # Confirms an ownership row cannot omit both supported holder types.
    def test_ownership_interest_rejects_no_holder(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OwnershipInterest.objects.create(
                held_entity=self.held_entity,
                bps=5000,
                valid_from=date(2020, 1, 1),
                provenance=self._provenance(5),
            )

    # Builds a complete legal entity without hiding fields relevant to the tests.
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

    # Builds one ownership provenance row with a controllable source line.
    def _provenance(self, line_number):
        return IngestionRecord.objects.create(
            source_file="interests.jsonl",
            line_number=line_number,
            record_type="HOLDS_INTEREST_IN",
            raw_payload={"line": line_number},
            status=IngestionRecord.Status.ACCEPTED,
            reason="",
        )
