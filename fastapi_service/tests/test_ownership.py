import unittest

from app.ownership import normalize_ownership


def relationship(holder="NP-001", held="LE-001", bps=5000, filing="F-001"):
    return {
        "relationship": "HOLDS_INTEREST_IN",
        "holder_type": "NaturalPerson",
        "holder_uid": holder,
        "held_entity_uid": held,
        "bps": bps,
        "valid_from": "2024-01-01",
        "valid_to": None,
        "filing_uid": filing,
    }


class OwnershipTests(unittest.TestCase):
    def test_current_and_as_of_response(self):
        path = {"nodes": [{"type": "NaturalPerson", "canonical_id": "NP-001", "display_name": "A"}, {"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "B"}], "relationships": [relationship()]}
        self.assertEqual(normalize_ownership("LE-001", [path], None)["temporal_mode"], "current")
        self.assertEqual(normalize_ownership("LE-001", [path], "2024-01-01")["temporal_mode"], "as_of")

    def test_direct_paths_cycles_and_self_loops(self):
        direct = {"nodes": [{"type": "NaturalPerson", "canonical_id": "NP-001", "display_name": "A"}, {"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "B"}], "relationships": [relationship()]}
        cycle = {"nodes": [{"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "B"}, {"type": "LegalEntity", "canonical_id": "LE-002", "display_name": "C"}, {"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "B"}], "relationships": [relationship("LE-001", "LE-002"), relationship("LE-002", "LE-001")]}
        result = normalize_ownership("LE-001", [direct, cycle], None)
        self.assertEqual(len(result["direct_owners"]), 1)
        self.assertTrue(result["upstream_paths"][1]["cycle"])

    def test_conflicts_and_duplicate_facts(self):
        nodes = [{"type": "NaturalPerson", "canonical_id": "NP-001", "display_name": "A"}, {"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "B"}]
        conflicting = normalize_ownership("LE-001", [{"nodes": nodes, "relationships": [relationship(bps=5000)]}, {"nodes": nodes, "relationships": [relationship(bps=6000, filing="F-002")]}], None)
        duplicate = normalize_ownership("LE-001", [{"nodes": nodes, "relationships": [relationship()]}, {"nodes": nodes, "relationships": [relationship()]}], None)
        self.assertTrue(conflicting["conflict"])
        self.assertFalse(duplicate["conflict"])

    def test_no_current_message(self):
        self.assertIn("No current ownership", normalize_ownership("LE-001", [], None)["message"])

    def test_nullable_filing_uid_stays_null_and_has_stable_id(self):
        path = {"nodes": [{"type": "NaturalPerson", "canonical_id": "NP-001", "display_name": "A"}, {"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "B"}], "relationships": [relationship(filing=None)]}
        fact = normalize_ownership("LE-001", [path], None)["direct_owners"][0]
        self.assertIsNone(fact["filing_uid"])
        self.assertIn(":null", fact["citation_id"])
        self.assertNotIn(":None", fact["citation_id"])
