import json
import tempfile
import unittest
from pathlib import Path

import run_eval


class EvaluationHarnessTests(unittest.TestCase):
    def test_taxonomy_uses_question_id_and_expected_outcome(self):
        original = run_eval.TAXONOMY
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "taxonomy.json"
            path.write_text(json.dumps({"questions": [{"question_id": "Q01", "class": "supported_entity", "expected_outcome": "answered"}]}))
            run_eval.TAXONOMY = path
            taxonomy = run_eval.load_taxonomy()
        run_eval.TAXONOMY = original
        self.assertEqual(run_eval.expected_status(taxonomy["Q01"]), "answered")

    def test_oracle_checks_relationships_and_negative_expectation(self):
        body = {
            "answer": "5000 basis points",
            "citations": [{"kind": "relationship", "details": {"holder_uid": "NP-001", "held_entity_uid": "LE-001", "bps": 5000}}],
        }
        self.assertTrue(run_eval.oracle_check({"required_relationships": [{"holder_uid": "NP-001", "held_entity_uid": "LE-001", "bps": 5000}], "expected_answer_tokens": ["5000"]}, body))
        self.assertFalse(run_eval.oracle_check({"expect_no_relationship_citations": True}, body))

    def test_fixture_reader_uses_held_uid_and_nullable_filing(self):
        original = run_eval.ROOT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "data/graph_seed"
            seed.mkdir(parents=True)
            (seed / "entities.jsonl").write_text('{"entity_uid":"LE-001"}\n')
            (seed / "persons.jsonl").write_text('{"person_uid":"NP-001"}\n')
            (seed / "interests.jsonl").write_text('{"holder_uid":"NP-001","held_uid":"LE-001","bps":5000,"valid_from":"2024-01-01","valid_to":null,"filing_uid":null}\n')
            run_eval.ROOT = root
            facts = run_eval.fixture_facts()
        run_eval.ROOT = original
        citation = {"kind": "relationship", "details": {"holder_uid": "NP-001", "held_entity_uid": "LE-001", "bps": 5000, "valid_from": "2024-01-01", "valid_to": None, "filing_uid": None}}
        self.assertTrue(run_eval.citations_valid([citation], facts))
