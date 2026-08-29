import unittest

from app.grounding import GroundingService, LocalEmbedder

from tests.support import test_settings


class FakeNeo4j:
    def __init__(self, exact=None):
        self.exact = exact or {}

    def resolve_exact(self, value):
        return self.exact.get(value, [])

    def grounding_nodes(self):
        return [
            {"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "One", "metadata": {}},
            {"type": "NaturalPerson", "canonical_id": "NP-001", "display_name": "Person", "metadata": {}},
        ]


class FakeStore:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.search_calls = 0
        self.documents = []

    def search(self, *args):
        self.search_calls += 1
        return self.rows

    def reset(self):
        self.reset_called = True

    def add_documents(self, documents, vectors):
        self.documents = documents
        self.vectors = vectors


class FakeEmbedder:
    def encode_one(self, text):
        return [0.0] * 384

    def encode_many(self, texts):
        return [[0.0] * 384 for _ in texts]


def match(kind, canonical_id, name, method="exact"):
    return {"type": kind, "canonical_id": canonical_id, "display_name": name, "metadata": {}, "match_method": method}


class GroundingTests(unittest.TestCase):
    def service(self, exact=None, rows=None):
        return GroundingService(test_settings(), FakeNeo4j(exact), FakeStore(rows), FakeEmbedder())

    def test_exact_identifier_and_duplicates_bypass_weaviate(self):
        service = self.service({"LE-001": [match("LegalEntity", "LE-001", "One")], "same": [match("LegalEntity", "LE-001", "Same"), match("LegalEntity", "LE-002", "Same")]})
        self.assertEqual(service.resolve_entity(" LE-001 ")[0]["canonical_id"], "LE-001")
        self.assertEqual(len(service.resolve_entity("same")), 2)
        self.assertEqual(service.store.search_calls, 0)

    def test_type_distinction_and_hybrid_verification(self):
        exact = {
            "Shared": [match("LegalEntity", "LE-001", "Shared"), match("NaturalPerson", "NP-001", "Shared")],
            "LE-010": [match("LegalEntity", "LE-010", "Live")],
            "NP-010": [match("LegalEntity", "LE-010", "Wrong type")],
        }
        rows = [
            {"node_type": "LegalEntity", "canonical_id": "LE-010"},
            {"node_type": "NaturalPerson", "canonical_id": "NP-010"},
            {"node_type": "LegalEntity", "canonical_id": "LE-stale"},
        ]
        service = self.service(exact, rows)
        self.assertEqual({item["type"] for item in service.resolve_entity("Shared")}, {"LegalEntity", "NaturalPerson"})
        self.assertEqual([item["canonical_id"] for item in service.resolve_entity("approximate")], ["LE-010"])

    def test_entity_candidates_are_deterministic(self):
        exact = {"LE-002": [match("LegalEntity", "LE-002", "Two")], "LE-001": [match("LegalEntity", "LE-001", "One")]}
        rows = [{"node_type": "LegalEntity", "canonical_id": "LE-002"}, {"node_type": "LegalEntity", "canonical_id": "LE-001"}]
        self.assertEqual([item["canonical_id"] for item in self.service(exact, rows).entity_candidates("owners")], ["LE-001", "LE-002"])

    def test_embedded_canonical_ids_use_exact_neo4j_resolution(self):
        exact = {
            "LE-005": [match("LegalEntity", "LE-005", "Five")],
            "NP-003": [match("NaturalPerson", "NP-003", "Person")],
            "LE-002": [match("LegalEntity", "LE-002", "Two")],
        }
        service = self.service(exact, [{"node_type": "LegalEntity", "canonical_id": "LE-001"}])
        self.assertEqual([item["canonical_id"] for item in service.entity_candidates("Who holds interests in LE-005?")], ["LE-005"])
        self.assertEqual([item["canonical_id"] for item in service.entity_candidates("What does np-003 hold?")], ["NP-003"])
        self.assertEqual([item["canonical_id"] for item in service.entity_candidates("Compare LE-005 and LE-002 and LE-005")], ["LE-002", "LE-005"])
        self.assertEqual(service.store.search_calls, 0)

    def test_unknown_embedded_identifier_does_not_fall_back_to_hybrid(self):
        service = self.service({}, [{"node_type": "LegalEntity", "canonical_id": "LE-001"}])
        self.assertEqual(service.entity_candidates("Who holds interests in LE-999?"), [])
        self.assertEqual(service.store.search_calls, 0)

    def test_candidate_name_in_question_uses_exact_neo4j_resolution(self):
        exact = {
            "Aqaba Logistics Park Company": [match("LegalEntity", "LE-005", "Aqaba Logistics Park Company")],
            "Meridian Capital Partners": [match("LegalEntity", "LE-010", "Meridian Capital Partners"), match("LegalEntity", "LE-011", "Meridian Capital Partners")],
        }
        rows = [
            {"node_type": "LegalEntity", "canonical_id": "LE-001", "display_name": "Other"},
            {"node_type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba Logistics Park Company"},
        ]
        service = self.service(exact, rows)
        result = service.entity_candidates("Which entities hold a direct interest in aqaba logistics park company today?")
        self.assertEqual([item["canonical_id"] for item in result], ["LE-005"])

        duplicate_service = self.service(exact, [{"node_type": "LegalEntity", "canonical_id": "LE-010", "display_name": "Meridian Capital Partners"}])
        duplicate_result = duplicate_service.entity_candidates("Who holds interests in Meridian Capital Partners?")
        self.assertEqual([item["canonical_id"] for item in duplicate_result], ["LE-010", "LE-011"])

    def test_hybrid_candidates_remain_when_no_name_is_in_question(self):
        exact = {"LE-001": [match("LegalEntity", "LE-001", "One")]}
        rows = [{"node_type": "LegalEntity", "canonical_id": "LE-001", "display_name": "One"}]
        service = self.service(exact, rows)
        self.assertEqual([item["canonical_id"] for item in service.entity_candidates("Which entities have owners?")], ["LE-001"])
        self.assertEqual(service.store.search_calls, 1)

    def test_rebuild_uses_supported_entities_and_capabilities_only(self):
        service = self.service()
        counts = service.rebuild()
        self.assertEqual(counts["entities"], 2)
        self.assertEqual(counts["capabilities"], 4)
        indexed = " ".join(document["text"] for document in service.store.documents)
        self.assertNotIn("eval_questions", indexed)

    def test_embedder_dimension_check(self):
        embedder = object.__new__(LocalEmbedder)
        embedder.settings = test_settings()
        with self.assertRaises(ValueError):
            embedder._check_dimension([0.0])
