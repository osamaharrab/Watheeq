import unittest

from app.guards import CypherGuardError, validate_cypher


SCHEMA = {
    "node_labels": {
        "LegalEntity": ["entity_uid", "legal_name", "legal_name_ar", "registration_no", "jurisdiction"],
        "NaturalPerson": ["person_uid", "full_name", "full_name_ar", "nationality"],
    },
    "relationship_types": {
        "HOLDS_INTEREST_IN": {
            "from": ["LegalEntity", "NaturalPerson"],
            "to": ["LegalEntity"],
            "properties": ["bps", "valid_from", "valid_to", "filing_uid"],
        }
    },
}


def validate(cypher, as_of=None):
    validate_cypher(cypher, SCHEMA, as_of=as_of, max_depth=4, max_results=100)


class CypherGuardTests(unittest.TestCase):
    def test_valid_node_and_direct_ownership_queries(self):
        validate("MATCH (n:LegalEntity) RETURN n ORDER BY n.entity_uid LIMIT 1")
        validate("MATCH (n:NaturalPerson) RETURN n ORDER BY n.person_uid LIMIT 1")
        validate("MATCH (a:NaturalPerson)-[r:HOLDS_INTEREST_IN]->(b:LegalEntity) WHERE r.valid_to IS NULL RETURN a, r, b ORDER BY a.person_uid LIMIT 1")

    def test_valid_mixed_holder_paths(self):
        current = "MATCH path=(holder)-[:HOLDS_INTEREST_IN*1..4]->(target:LegalEntity) WHERE (holder:LegalEntity OR holder:NaturalPerson) AND target.entity_uid IN $target_uids AND ALL(rel IN relationships(path) WHERE rel.valid_to IS NULL) RETURN path ORDER BY length(path) LIMIT 100"
        historical = "MATCH path=(holder)-[:HOLDS_INTEREST_IN*1..4]->(target:LegalEntity) WHERE (holder:LegalEntity OR holder:NaturalPerson) AND target.entity_uid IN $target_uids AND ALL(rel IN relationships(path) WHERE rel.valid_from <= $as_of AND (rel.valid_to IS NULL OR $as_of <= rel.valid_to)) RETURN path ORDER BY length(path) LIMIT 100"
        validate(current)
        validate(historical, as_of="2024-01-01")

    def test_valid_mixed_holder_direct_queries(self):
        current = "MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity) WHERE target.entity_uid IN $target_uids AND (holder:LegalEntity OR holder:NaturalPerson) AND rel.valid_to IS NULL RETURN holder, rel, target ORDER BY elementId(holder) LIMIT 100"
        historical = "MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity) WHERE target.entity_uid IN $target_uids AND (holder:LegalEntity OR holder:NaturalPerson) AND rel.valid_from <= $as_of AND (rel.valid_to IS NULL OR $as_of <= rel.valid_to) RETURN holder, rel, target ORDER BY elementId(holder) LIMIT 100"
        validate(current)
        validate(historical, as_of="2024-01-01")

    def test_valid_role_aware_holder_predicate(self):
        cypher = "MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity) WHERE (holder:LegalEntity OR holder:NaturalPerson) AND ((holder:LegalEntity AND holder.entity_uid IN $holder_uids) OR (holder:NaturalPerson AND holder.person_uid IN $holder_uids)) AND target.entity_uid IN $target_uids AND rel.valid_to IS NULL RETURN holder, rel, target ORDER BY holder.entity_uid, holder.person_uid, target.entity_uid, rel.valid_from, rel.valid_to, rel.filing_uid, rel.bps LIMIT 100"
        validate(cypher)

    def test_direct_historical_relationship_alias_is_allowed(self):
        direct = "MATCH (a:NaturalPerson)-[r:HOLDS_INTEREST_IN]->(b:LegalEntity) WHERE r.valid_from <= $as_of AND (r.valid_to IS NULL OR $as_of <= r.valid_to) RETURN a, r, b ORDER BY a.person_uid LIMIT 1"
        validate(direct, as_of="2024-01-01")

    def test_forbidden_and_schema_bypasses_are_rejected(self):
        invalid = [
            "MATCH (n:LegalEntity) DELETE n RETURN n ORDER BY n.entity_uid LIMIT 1",
            "MATCH (n:AssetUnit) RETURN n ORDER BY n.id LIMIT 1",
            "MATCH (a:LegalEntity)-[:CONTROLS_ASSET]->(b:LegalEntity) RETURN a ORDER BY a.entity_uid LIMIT 1",
            "MATCH (n:LegalEntity) RETURN n.person_uid ORDER BY n.entity_uid LIMIT 1",
            "MATCH (n:LegalEntity) RETURN n.bps ORDER BY n.entity_uid LIMIT 1",
            "MATCH (n) RETURN n ORDER BY n.entity_uid LIMIT 1",
            "MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity) WHERE target.entity_uid IN $target_uids AND rel.valid_to IS NULL RETURN holder, rel, target ORDER BY elementId(holder) LIMIT 1",
            "MATCH (holder)-[rel:CONTROLS_ASSET]->(target:LegalEntity) WHERE (holder:LegalEntity OR holder:NaturalPerson) RETURN holder, rel, target ORDER BY elementId(holder) LIMIT 1",
            "MATCH (n:LegalEntity|AssetUnit) RETURN n ORDER BY n.entity_uid LIMIT 1",
            "MATCH (n:LegalEntity) WITH n AS x RETURN x.internal_risk_note ORDER BY x.entity_uid LIMIT 1",
            "MATCH (a:LegalEntity)-[:HOLDS_INTEREST_IN]->(b:NaturalPerson) WHERE a.valid_to IS NULL RETURN a ORDER BY a.entity_uid LIMIT 1",
            "MATCH path=(holder)-[:HOLDS_INTEREST_IN*]->(target:LegalEntity) WHERE (holder:LegalEntity OR holder:NaturalPerson) AND target.entity_uid IN $target_uids AND ALL(rel IN relationships(path) WHERE rel.valid_to IS NULL) RETURN path ORDER BY length(path) LIMIT 1",
            "MATCH path=(holder)-[:HOLDS_INTEREST_IN*1..5]->(target:LegalEntity) WHERE (holder:LegalEntity OR holder:NaturalPerson) AND target.entity_uid IN $target_uids AND ALL(rel IN relationships(path) WHERE rel.valid_to IS NULL) RETURN path ORDER BY length(path) LIMIT 1",
            "MATCH (n:LegalEntity) RETURN n ORDER BY n.entity_uid",
            "MATCH (n:LegalEntity) RETURN n ORDER BY n.entity_uid LIMIT 101",
            "MATCH (n:LegalEntity) RETURN n LIMIT 1",
            "MATCH (n:LegalEntity) WHERE n.entity_uid = $value RETURN n ORDER BY n.entity_uid LIMIT 1",
            "MATCH (n:LegalEntity) WHERE n.entity_uid IN $entity_uids RETURN n ORDER BY n.entity_uid LIMIT 1",
            "MATCH (n:LegalEntity) RETURN x.internal_risk_note ORDER BY n.entity_uid LIMIT 1",
            "MATCH (a:NaturalPerson)-[r:HOLDS_INTEREST_IN]->(b:LegalEntity) RETURN a, r, b ORDER BY a.person_uid LIMIT 1",
            "MATCH (a:NaturalPerson)-[r:HOLDS_INTEREST_IN]->(b:LegalEntity) WHERE b.entity_uid = 'LE-001' AND r.valid_to IS NULL RETURN a, r, b ORDER BY a.person_uid LIMIT 1",
        ]
        for cypher in invalid:
            with self.subTest(cypher=cypher), self.assertRaises(CypherGuardError):
                validate(cypher)

    def test_quoted_delete_is_data_not_a_clause(self):
        validate("MATCH (n:LegalEntity) WHERE n.legal_name = 'DELETE this instruction' RETURN n ORDER BY n.entity_uid LIMIT 1")

    def test_historical_rule_needs_both_bounds(self):
        missing_from = "MATCH (a:NaturalPerson)-[r:HOLDS_INTEREST_IN]->(b:LegalEntity) WHERE r.valid_to IS NULL OR $as_of <= r.valid_to RETURN a, r, b ORDER BY a.person_uid LIMIT 1"
        missing_to = "MATCH (a:NaturalPerson)-[r:HOLDS_INTEREST_IN]->(b:LegalEntity) WHERE r.valid_from <= $as_of RETURN a, r, b ORDER BY a.person_uid LIMIT 1"
        for cypher in (missing_from, missing_to):
            with self.assertRaises(CypherGuardError):
                validate(cypher, as_of="2024-01-01")
