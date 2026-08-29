import unittest
from datetime import date

from app.clients.django import AuditUnavailable
from app.clients.neo4j import QueryBoundedError
from app.clients.ollama import ModelUnavailable, PlannerOutputError
from app.pipeline import AskPipeline, _cypher_prompt
from app.schemas import AskRequest, Text2CypherOutput

from tests.support import test_settings


def current_query(kind):
    holder_filter = """(holder:LegalEntity OR holder:NaturalPerson)
  AND ((holder:LegalEntity AND holder.entity_uid IN $holder_uids)
       OR (holder:NaturalPerson AND holder.person_uid IN $holder_uids))"""
    order = "holder.entity_uid, holder.person_uid, target.entity_uid, rel.valid_from, rel.valid_to, rel.filing_uid, rel.bps"
    if kind == "incoming_ownership":
        where = "target.entity_uid IN $target_uids AND (holder:LegalEntity OR holder:NaturalPerson)"
    elif kind == "outgoing_ownership":
        where = holder_filter
    elif kind == "relationship_check":
        where = f"{holder_filter} AND target.entity_uid IN $target_uids"
    elif kind == "ownership_relationships":
        where = "(holder:LegalEntity OR holder:NaturalPerson)"
    else:
        return """MATCH path=(holder)-[:HOLDS_INTEREST_IN*1..4]->(target:LegalEntity)
WHERE target.entity_uid IN $target_uids
  AND (holder:LegalEntity OR holder:NaturalPerson)
  AND ALL(rel IN relationships(path) WHERE rel.valid_to IS NULL)
RETURN path
ORDER BY length(path), elementId(holder)
LIMIT 3"""
    return f"""MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity)
WHERE {where}
  AND rel.valid_to IS NULL
RETURN holder, rel, target
ORDER BY {order}
LIMIT 3"""


def historical_query(kind):
    return current_query(kind).replace(
        "AND rel.valid_to IS NULL",
        "AND rel.valid_from <= $as_of AND (rel.valid_to IS NULL OR $as_of <= rel.valid_to)",
    ).replace(
        "ALL(rel IN relationships(path) WHERE rel.valid_to IS NULL)",
        "ALL(rel IN relationships(path) WHERE rel.valid_from <= $as_of AND (rel.valid_to IS NULL OR $as_of <= rel.valid_to))",
    )


def plan(kind, *, holders=None, targets=None, mode="facts", cypher=None):
    return Text2CypherOutput(
        action="query",
        query_kind=kind,
        answer_mode=mode,
        holder_mentions=holders or [],
        target_mentions=targets or [],
        cypher=cypher or current_query(kind),
        reason="",
    )


def relationship(holder_uid, target_uid, bps, valid_from, valid_to=None, filing_uid="FL-001", holder_name=None, target_name=None):
    start = {"person_uid": holder_uid} if holder_uid.startswith("NP-") else {"entity_uid": holder_uid}
    if holder_name:
        start["full_name" if holder_uid.startswith("NP-") else "legal_name"] = holder_name
    end = {"entity_uid": target_uid}
    if target_name:
        end["legal_name"] = target_name
    return {
        "rel": {
            "kind": "relationship",
            "type": "HOLDS_INTEREST_IN",
            "start": {"kind": "node", "properties": start},
            "end": {"kind": "node", "properties": end},
            "properties": {
                "bps": bps,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "filing_uid": filing_uid,
            },
        }
    }


class FakeGrounding:
    def __init__(self, matches=None, candidates=None):
        self.matches = matches or {}
        self.candidates = candidates or []
        self.resolve_calls = []
        self.candidate_calls = []

    def resolve_entity(self, mention):
        self.resolve_calls.append(mention)
        return self.matches.get(mention, [])

    def entity_candidates(self, question):
        self.candidate_calls.append(question)
        return self.candidates


class FakeOllama:
    def __init__(self, output):
        self.output = output
        self.prompts = []

    def generate_cypher(self, prompt):
        self.prompts.append(prompt)
        return self.output


class FakeNeo4j:
    def __init__(self, rows=None, error=None):
        self.rows = rows if rows is not None else []
        self.error = error
        self.calls = []

    def execute_read(self, cypher, parameters):
        self.calls.append((cypher, parameters))
        if self.error:
            raise self.error
        return self.rows


class FakeDjango:
    def __init__(self, error=None):
        self.payloads = []
        self.error = error

    def create_audit(self, payload):
        if self.error:
            raise self.error
        self.payloads.append(payload)


class PipelineTests(unittest.TestCase):
    def pipeline(self, output, *, matches=None, candidates=None, rows=None, neo4j=None, django=None):
        return AskPipeline(
            test_settings(),
            FakeGrounding(matches, candidates),
            neo4j or FakeNeo4j(rows),
            FakeOllama(output),
            django or FakeDjango(),
        )

    def test_prompt_has_only_ownership_templates_and_role_parameters(self):
        prompt = _cypher_prompt(
            AskRequest(question="Who owns LE-005?"),
            [],
            test_settings(max_query_results=100),
        )
        self.assertIn('"query_kind"', prompt)
        self.assertIn("$holder_uids", prompt)
        self.assertIn("$target_uids", prompt)
        self.assertNotIn("ENTITY FACT template", prompt)
        self.assertIn("Classify the requested information first", prompt)
        self.assertIn("Hints identify entities", prompt)
        self.assertIn("Generic categories such as natural persons", prompt)
        self.assertIn("Holder Alpha", prompt)
        self.assertNotIn("registration_no", prompt)
        self.assertIn('If action="query", query_kind MUST be a supported ownership query kind', prompt)
        self.assertIn('NEVER return action="query" with query_kind=null, answer_mode=null, or cypher=null', prompt)
        self.assertIn('return action="abstain" instead', prompt)
        self.assertIn('verify every action="query" has a non-null query_kind, answer_mode, and cypher', prompt)
        self.assertIn("holders may be LegalEntity or NaturalPerson", prompt)
        self.assertIn("holder.entity_uid IN $holder_uids and holder.person_uid IN $holder_uids branches", prompt)
        self.assertIn("Never simplify it to only one branch", prompt)

    def test_specific_stake_uses_relationship_check_with_both_endpoints(self):
        holder = {
            "type": "NaturalPerson",
            "canonical_id": "NP-900",
            "display_name": "Holder Alpha",
            "metadata": {},
            "match_method": "exact",
        }
        target = {
            "type": "LegalEntity",
            "canonical_id": "LE-900",
            "display_name": "Target Beta",
            "metadata": {},
            "match_method": "exact",
        }
        planner_output = plan(
            "relationship_check",
            holders=["NP-900"],
            targets=["LE-900"],
        )
        pipeline = self.pipeline(
            planner_output,
            matches={"NP-900": [holder], "LE-900": [target]},
            candidates=[holder, target],
            rows=[relationship("NP-900", "LE-900", 4200, "2020-01-01")],
        )

        result, _ = pipeline.ask(
            AskRequest(
                question="What ownership stake does Holder Alpha currently hold in Target Beta?"
            )
        )

        self.assertEqual(planner_output.query_kind, "relationship_check")
        self.assertEqual(planner_output.holder_mentions, ["NP-900"])
        self.assertEqual(planner_output.target_mentions, ["LE-900"])
        self.assertEqual(result.status, "answered")
        self.assertEqual(
            pipeline.neo4j.calls[0][1],
            {"holder_uids": ["NP-900"], "target_uids": ["LE-900"]},
        )

    def test_exact_entity_node_property_and_other_domain_requests_are_unsupported(self):
        entity = {
            "type": "LegalEntity",
            "canonical_id": "LE-900",
            "display_name": "Example Holdings Ltd",
            "metadata": {},
            "match_method": "exact",
        }
        for question in (
            "Which registry code belongs to Example Holdings Ltd?",
            "Which collateral links involve Example Holdings Ltd?",
        ):
            with self.subTest(question=question):
                django = FakeDjango()
                grounding = FakeGrounding(candidates=[entity])
                neo4j = FakeNeo4j()
                pipeline = AskPipeline(
                    test_settings(),
                    grounding,
                    neo4j,
                    FakeOllama(Text2CypherOutput(action="unsupported", reason="outside")),
                    django,
                )

                result, _ = pipeline.ask(AskRequest(question=question))

                self.assertEqual(result.status, "unsupported")
                self.assertEqual(result.resolved_entities, [])
                self.assertEqual(result.citations, [])
                self.assertEqual(result.conflicts, [])
                self.assertEqual(grounding.candidate_calls, [])
                self.assertEqual(grounding.resolve_calls, [])
                self.assertEqual(pipeline.ollama.prompts, [])
                self.assertEqual(neo4j.calls, [])
                self.assertIsNone(django.payloads[0]["generated_cypher"])
                self.assertFalse(django.payloads[0]["cypher_executed"])

    def test_generic_holder_type_filters_do_not_become_entity_mentions(self):
        target = {
            "type": "LegalEntity",
            "canonical_id": "LE-900",
            "display_name": "Example Holdings Ltd",
            "metadata": {},
            "match_method": "exact",
        }
        type_queries = {
            "NaturalPerson": (
                "Which natural persons directly hold an interest in Example Holdings Ltd?",
                "NP-900",
                "holder.person_uid",
            ),
            "LegalEntity": (
                "Which legal entities directly hold an interest in Example Holdings Ltd?",
                "LE-901",
                "holder.entity_uid",
            ),
        }
        for label, (question, holder_uid, holder_order) in type_queries.items():
            with self.subTest(label=label):
                cypher = f"""MATCH (holder:{label})-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity)
WHERE target.entity_uid IN $target_uids
  AND rel.valid_to IS NULL
RETURN holder, rel, target
ORDER BY {holder_order}, target.entity_uid, rel.valid_from, rel.valid_to, rel.filing_uid, rel.bps
LIMIT 3"""
                pipeline = self.pipeline(
                    plan("incoming_ownership", targets=["Example Holdings Ltd"], cypher=cypher),
                    matches={"Example Holdings Ltd": [target]},
                    candidates=[target],
                    rows=[relationship(holder_uid, "LE-900", 5000, "2020-01-01")],
                )

                result, _ = pipeline.ask(AskRequest(question=question))

                self.assertEqual(result.status, "answered")
                self.assertEqual(pipeline.grounding.resolve_calls, ["Example Holdings Ltd"])
                self.assertEqual(pipeline.neo4j.calls[0][1], {"target_uids": ["LE-900"]})

    def test_ownership_completeness_requests_abstain_before_graph_execution(self):
        entity = {
            "type": "LegalEntity",
            "canonical_id": "LE-900",
            "display_name": "Example Holdings Ltd",
            "metadata": {},
            "match_method": "exact",
        }
        for question in (
            "Do ownership interests in Example Holdings Ltd add up to the full amount?",
            "Is any ownership stake in Example Holdings Ltd missing from the register?",
        ):
            with self.subTest(question=question):
                pipeline = self.pipeline(
                    Text2CypherOutput(action="abstain", reason="ownership arithmetic"),
                    candidates=[entity],
                )

                result, _ = pipeline.ask(AskRequest(question=question))

                self.assertEqual(result.status, "abstained")
                self.assertEqual(result.resolved_entities, [])
                self.assertEqual(pipeline.neo4j.calls, [])

    def test_scope_gate_handles_years_only_for_ownership_questions(self):
        outside = self.pipeline(Text2CypherOutput(action="unsupported", reason="outside"))
        result, _ = outside.ask(
            AskRequest(question="What registry field existed for Target Beta in 2017?")
        )
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(outside.ollama.prompts, [])
        self.assertEqual(outside.neo4j.calls, [])

        ownership = self.pipeline(plan("incoming_ownership", targets=["Target Beta"]))
        result, _ = ownership.ask(
            AskRequest(question="Who owned Target Beta in 2017?")
        )
        self.assertEqual(result.status, "abstained")
        self.assertEqual(ownership.ollama.prompts, [])
        self.assertEqual(ownership.neo4j.calls, [])

    def test_upstream_ownership_wording_uses_the_bounded_query_kind(self):
        target = {
            "type": "LegalEntity",
            "canonical_id": "LE-900",
            "display_name": "Target Beta",
            "metadata": {},
            "match_method": "exact",
        }
        pipeline = self.pipeline(
            plan("upstream_ownership", targets=["LE-900"]),
            matches={"LE-900": [target]},
            candidates=[target],
            rows=[relationship("LE-901", "LE-900", 6000, "2020-01-01")],
        )

        result, _ = pipeline.ask(
            AskRequest(question="Trace the ultimate owners of Target Beta.")
        )

        self.assertEqual(result.status, "answered")
        self.assertEqual(pipeline.neo4j.calls[0][1], {"target_uids": ["LE-900"]})

    def test_exact_entity_hints_reach_the_planner_and_relationship_check_uses_both_roles(self):
        person = {"type": "NaturalPerson", "canonical_id": "NP-003", "display_name": "Faisal Nusseibeh", "metadata": {}, "match_method": "exact"}
        entity = {"type": "LegalEntity", "canonical_id": "LE-006", "display_name": "Cedar Ridge Investments Ltd", "metadata": {}, "match_method": "exact"}
        pipeline = self.pipeline(
            plan(
                "relationship_check",
                holders=["Faisal Nusseibeh"],
                targets=["Cedar Ridge Investments Ltd"],
                mode="exists",
            ),
            matches={
                "Faisal Nusseibeh": [person],
                "Cedar Ridge Investments Ltd": [entity],
            },
            candidates=[person, entity],
            rows=[relationship("NP-003", "LE-006", 5100, "2009-06-30")],
        )

        result, _ = pipeline.ask(
            AskRequest(
                question="Does Faisal Nusseibeh hold an interest in Cedar Ridge Investments Ltd?"
            )
        )

        prompt = pipeline.ollama.prompts[0]
        self.assertIn('"canonical_id": "NP-003"', prompt)
        self.assertIn('"canonical_id": "LE-006"', prompt)
        self.assertEqual(result.status, "answered")
        self.assertEqual(len(pipeline.ollama.prompts), 1)
        self.assertEqual(
            pipeline.neo4j.calls[0][1],
            {"holder_uids": ["NP-003"], "target_uids": ["LE-006"]},
        )

    def test_hybrid_candidates_are_not_exact_planning_hints(self):
        hybrid = {"type": "LegalEntity", "canonical_id": "LE-006", "display_name": "maqluba", "metadata": {}, "match_method": "hybrid"}
        pipeline = self.pipeline(
            Text2CypherOutput(action="unsupported", reason="outside"),
            candidates=[hybrid],
        )

        result, _ = pipeline.ask(AskRequest(question="Who owns Target Beta?"))

        self.assertEqual(result.status, "unsupported")
        self.assertIn("Verified exact entity hints: []", pipeline.ollama.prompts[0])
        self.assertEqual(pipeline.neo4j.calls, [])

    def test_incomplete_plan_that_drops_an_exact_entity_abstains_before_graph_execution(self):
        person = {"type": "NaturalPerson", "canonical_id": "NP-003", "display_name": "Faisal Nusseibeh", "metadata": {}, "match_method": "exact"}
        entity = {"type": "LegalEntity", "canonical_id": "LE-006", "display_name": "Cedar Ridge Investments Ltd", "metadata": {}, "match_method": "exact"}
        django = FakeDjango()
        pipeline = self.pipeline(
            plan("incoming_ownership", targets=["Cedar Ridge Investments Ltd"]),
            matches={"Cedar Ridge Investments Ltd": [entity]},
            candidates=[person, entity],
            rows=[
                relationship("NP-003", "LE-006", 5100, "2009-06-30"),
                relationship("NP-004", "LE-006", 4900, "2009-06-30"),
            ],
            django=django,
        )

        result, _ = pipeline.ask(
            AskRequest(
                question="Does Faisal Nusseibeh hold an interest in Cedar Ridge Investments Ltd?"
            )
        )

        self.assertEqual(result.status, "abstained")
        self.assertEqual(
            result.answer,
            "The ownership query could not preserve all explicit entity references safely.",
        )
        self.assertEqual(result.resolved_entities, [])
        self.assertEqual(result.citations, [])
        self.assertEqual(result.conflicts, [])
        self.assertEqual(pipeline.neo4j.calls, [])
        self.assertFalse(django.payloads[0]["cypher_executed"])

    def test_current_and_historical_incoming_facts_keep_marker_mapping(self):
        matches = {"LE-005": [{"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}]}
        current_rows = [
            relationship("LE-006", "LE-005", 2000, "2025-09-14"),
            relationship("LE-007", "LE-005", 8000, "2025-09-14"),
        ]
        current, _ = self.pipeline(
            plan("incoming_ownership", targets=["LE-005"]),
            matches=matches,
            candidates=matches["LE-005"],
            rows=current_rows,
        ).ask(AskRequest(question="Who holds interests in LE-005?"))
        self.assertEqual(current.answer, "Ownership relationships: LE-006 (2000 bps) [1] and LE-007 (8000 bps) [2].")
        self.assertEqual([citation.details["bps"] for citation in current.citations], [2000, 8000])

        named_matches = {"Aqaba Logistics Park Company": matches["LE-005"]}
        named, _ = self.pipeline(plan("incoming_ownership", targets=["Aqaba Logistics Park Company"]), matches=named_matches, rows=current_rows).ask(AskRequest(question="Who owns part of Aqaba Logistics Park Company?"))
        self.assertEqual(named.status, "answered")

        historical_rows = [
            relationship("LE-006", "LE-005", 7000, "2013-11-27", "2025-09-14", "FL-101"),
            relationship("LE-007", "LE-005", 3000, "2013-11-27", "2025-09-14", "FL-101"),
        ]
        historical_plan = plan("incoming_ownership", targets=["LE-005"], cypher=historical_query("incoming_ownership"))
        historical_pipeline = self.pipeline(historical_plan, matches=matches, rows=historical_rows)
        historical, _ = historical_pipeline.ask(AskRequest(question="Who held interests?", as_of=date(2025, 9, 13)))
        self.assertIn("LE-006 (7000 bps) [1]", historical.answer)
        self.assertIn("LE-007 (3000 bps) [2]", historical.answer)
        self.assertEqual(historical_pipeline.neo4j.calls[0][1], {"target_uids": ["LE-005"], "as_of": date(2025, 9, 13)})

    def test_outgoing_natural_person_by_id_and_name_uses_holder_role(self):
        person = {"type": "NaturalPerson", "canonical_id": "NP-003", "display_name": "Faisal Nusseibeh", "metadata": {}, "match_method": "exact"}
        for mention in ("NP-003", "Faisal Nusseibeh"):
            with self.subTest(mention=mention):
                pipeline = self.pipeline(
                    plan("outgoing_ownership", holders=[mention]),
                    matches={mention: [person]},
                    rows=[relationship("NP-003", "LE-006", 5100, "2009-06-30")],
                )
                result, _ = pipeline.ask(AskRequest(question="Which entities does Faisal hold interests in?"))
                self.assertEqual(result.status, "answered")
                self.assertIn("LE-006 (5100 bps) [1]", result.answer)
                self.assertEqual(pipeline.neo4j.calls[0][1], {"holder_uids": ["NP-003"]})

        historical = self.pipeline(
            plan("outgoing_ownership", holders=["NP-003"], cypher=historical_query("outgoing_ownership")),
            matches={"NP-003": [person]},
            rows=[relationship("NP-003", "LE-006", 5100, "2009-06-30")],
        )
        result, _ = historical.ask(AskRequest(question="Which entities did NP-003 hold interests in?", as_of=date(2010, 1, 1)))
        self.assertEqual(historical.neo4j.calls[0][1], {"holder_uids": ["NP-003"], "as_of": date(2010, 1, 1)})
        self.assertIn("LE-006 (5100 bps) [1]", result.answer)

    def test_outgoing_legal_entity_and_relationship_check_use_separate_roles(self):
        entity = {"type": "LegalEntity", "canonical_id": "LE-006", "display_name": "Cedar Ridge", "metadata": {}, "match_method": "exact"}
        target = {"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}
        outgoing = self.pipeline(
            plan("outgoing_ownership", holders=["LE-006"]),
            matches={"LE-006": [entity]},
            rows=[relationship("LE-006", "LE-005", 2000, "2025-09-14")],
        )
        outgoing_result, _ = outgoing.ask(AskRequest(question="What entities does LE-006 hold interests in?"))
        self.assertIn("LE-005 (2000 bps) [1]", outgoing_result.answer)

        person = {"type": "NaturalPerson", "canonical_id": "NP-003", "display_name": "Faisal", "metadata": {}, "match_method": "exact"}
        check = self.pipeline(
            plan("relationship_check", holders=["Faisal"], targets=["Cedar Ridge"], mode="exists"),
            matches={"Faisal": [person], "Cedar Ridge": [entity]},
            rows=[relationship("NP-003", "LE-006", 5100, "2009-06-30")],
        )
        check_result, _ = check.ask(AskRequest(question="Does Faisal hold an interest in Cedar Ridge?"))
        self.assertTrue(check_result.answer.startswith("Yes."))
        self.assertEqual(check.neo4j.calls[0][1], {"holder_uids": ["NP-003"], "target_uids": ["LE-006"]})
        self.assertEqual(len(check_result.citations), 1)

        legal_check = self.pipeline(
            plan("relationship_check", holders=["LE-006"], targets=["LE-005"], mode="exists"),
            matches={"LE-006": [entity], "LE-005": [target]},
            rows=[relationship("LE-006", "LE-005", 2000, "2025-09-14")],
        )
        legal_result, _ = legal_check.ask(AskRequest(question="Does LE-006 hold an interest in LE-005?"))
        self.assertTrue(legal_result.answer.startswith("Yes."))
        self.assertEqual(legal_check.neo4j.calls[0][1], {"holder_uids": ["LE-006"], "target_uids": ["LE-005"]})

    def test_historical_relationship_check_and_boundary_conflicts_preserve_all_facts(self):
        matches = {
            "LE-006": [{"type": "LegalEntity", "canonical_id": "LE-006", "display_name": "Cedar", "metadata": {}, "match_method": "exact"}],
            "LE-005": [{"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}],
        }
        historical = self.pipeline(
            plan("relationship_check", holders=["LE-006"], targets=["LE-005"], cypher=historical_query("relationship_check")),
            matches=matches,
            rows=[relationship("LE-006", "LE-005", 7000, "2013-11-27", "2025-09-14", "FL-101")],
        )
        result, _ = historical.ask(AskRequest(question="What ownership stake does LE-006 hold in LE-005?", as_of=date(2025, 9, 13)))
        self.assertIn("LE-006 holds 7000 bps in LE-005, effective from 2013-11-27 until 2025-09-14 under filing FL-101 [1]", result.answer)

        boundary_rows = [
            relationship("LE-006", "LE-005", 2000, "2025-09-14", None, "FL-102"),
            relationship("LE-006", "LE-005", 7000, "2013-11-27", "2025-09-14", "FL-101"),
            relationship("LE-007", "LE-005", 3000, "2013-11-27", "2025-09-14", "FL-101"),
            relationship("LE-007", "LE-005", 8000, "2025-09-14", None, "FL-102"),
        ]
        boundary = self.pipeline(
            plan("incoming_ownership", targets=["LE-005"], cypher=historical_query("incoming_ownership")),
            matches={"LE-005": matches["LE-005"]},
            rows=boundary_rows,
        )
        conflict, _ = boundary.ask(AskRequest(question="Who held interests in LE-005?", as_of=date(2025, 9, 14)))
        self.assertTrue(conflict.conflicts)
        for fact in ("LE-006 (2000 bps) [1]", "LE-006 (7000 bps) [2]", "LE-007 (3000 bps) [3]", "LE-007 (8000 bps) [4]"):
            self.assertIn(fact, conflict.answer)
        self.assertEqual(len(conflict.citations), 4)

    def test_relationship_count_uses_verified_relationship_facts(self):
        result, _ = self.pipeline(
            plan("incoming_ownership", targets=["LE-005"], mode="count"),
            matches={"LE-005": [{"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}]},
            rows=[relationship("LE-006", "LE-005", 2000, "2025-09-14"), relationship("LE-007", "LE-005", 8000, "2025-09-14")],
        ).ask(AskRequest(question="How many direct holders does LE-005 have?"))
        self.assertTrue(result.answer.startswith("2 direct holder(s) found."))
        self.assertEqual(len(result.citations), 2)

        relationship_set, _ = self.pipeline(
            plan("ownership_relationships", mode="count"),
            rows=[relationship("LE-006", "LE-005", 2000, "2025-09-14"), relationship("LE-007", "LE-005", 8000, "2025-09-14")],
        ).ask(AskRequest(question="How many current ownership relationships are represented?"))
        self.assertTrue(relationship_set.answer.startswith("2 verified ownership relationship(s) found."))

    def test_unsupported_questions_do_not_resolve_or_execute(self):
        for question in ("What is the capital of Japan?", "How do I cook maqluba?", "What is Messi's salary?", "What is the weather?", "List all company names.", "How many companies are in the database?", "What is the registration number of LE-005?", "What is the status of LE-005?"):
            with self.subTest(question=question):
                candidate = {
                    "type": "LegalEntity",
                    "canonical_id": "LE-005",
                    "display_name": "Aqaba",
                    "metadata": {},
                    "match_method": "exact" if "LE-005" in question else "hybrid",
                }
                django = FakeDjango()
                grounding = FakeGrounding({"LE-005": [candidate]}, candidates=[candidate])
                neo4j = FakeNeo4j()
                pipeline = AskPipeline(test_settings(), grounding, neo4j, FakeOllama(Text2CypherOutput(action="unsupported", reason="outside")), django)
                result, _ = pipeline.ask(AskRequest(question=question))
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(result.resolved_entities, [])
                self.assertEqual(result.citations, [])
                self.assertEqual(result.conflicts, [])
                self.assertEqual(grounding.resolve_calls, [])
                self.assertEqual(pipeline.ollama.prompts, [])
                self.assertEqual(neo4j.calls, [])
                self.assertIsNone(django.payloads[0]["generated_cypher"])
                self.assertFalse(django.payloads[0]["cypher_executed"])

    def test_ambiguous_unknown_and_zero_result_queries_abstain_without_negative_claim(self):
        ambiguous = self.pipeline(
            plan("incoming_ownership", targets=["Ambiguous"]),
            matches={"Ambiguous": [
                {"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "One", "metadata": {}, "match_method": "exact"},
                {"type": "LegalEntity", "canonical_id": "LE-006", "display_name": "Two", "metadata": {}, "match_method": "exact"},
            ]},
        )
        result, _ = ambiguous.ask(AskRequest(question="Who owns Ambiguous?"))
        self.assertEqual(result.status, "abstained")
        self.assertEqual(ambiguous.neo4j.calls, [])

        unknown = self.pipeline(plan("incoming_ownership", targets=["Unknown"]), matches={"Unknown": []})
        result, _ = unknown.ask(AskRequest(question="Who owns Unknown?"))
        self.assertEqual(result.status, "abstained")
        self.assertEqual(unknown.neo4j.calls, [])

        duplicate = [
            {"type": "LegalEntity", "canonical_id": "LE-900", "display_name": "Duplicate Target", "metadata": {}, "match_method": "exact"},
            {"type": "LegalEntity", "canonical_id": "LE-901", "display_name": "Duplicate Target", "metadata": {}, "match_method": "exact"},
        ]
        duplicate_name = self.pipeline(
            plan("incoming_ownership", targets=["Duplicate Target"]),
            matches={"Duplicate Target": duplicate},
            candidates=duplicate,
        )
        result, _ = duplicate_name.ask(AskRequest(question="Who owns Duplicate Target?"))
        self.assertEqual(result.status, "abstained")
        self.assertEqual(duplicate_name.neo4j.calls, [])

        zero = self.pipeline(plan("incoming_ownership", targets=["LE-005"]), matches={"LE-005": [{"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}]}, rows=[])
        result, _ = zero.ask(AskRequest(question="Who owns LE-005?"))
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.answer, "No citable ownership relationship was found for the supplied entities and date.")

    def test_one_planning_call_audits_answers_and_preserves_error_outcomes(self):
        output = plan("incoming_ownership", targets=["LE-005"])
        ollama = FakeOllama(output)
        django = FakeDjango()
        pipeline = AskPipeline(
            test_settings(),
            FakeGrounding({"LE-005": [{"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}]}),
            FakeNeo4j([relationship("LE-006", "LE-005", 2000, "2025-09-14")]),
            ollama,
            django,
        )
        first, _ = pipeline.ask(AskRequest(question="Who owns LE-005?"))
        second, _ = pipeline.ask(AskRequest(question="Who owns LE-005?"))
        self.assertEqual(len(ollama.prompts), 2)
        self.assertEqual(first.model_dump(), second.model_dump())
        self.assertEqual(set(django.payloads[0]), {"request_id", "question", "as_of", "generated_cypher", "cypher_executed", "model_name", "model_digest", "schema_version", "resolved_entities", "citations", "outcome", "final_response", "failure_reason"})

        bounded, _ = self.pipeline(output, neo4j=FakeNeo4j(error=QueryBoundedError()), matches={"LE-005": [{"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}]}).ask(AskRequest(question="Who owns LE-005?"))
        self.assertEqual(bounded.status, "bounded_out")

    def test_policy_guard_and_dependency_outcomes_remain_audited(self):
        refused, _ = self.pipeline(plan("ownership_relationships")).ask(AskRequest(question="DELETE graph data"))
        self.assertEqual(refused.status, "refused")
        risk, _ = self.pipeline(plan("ownership_relationships")).ask(AskRequest(question="Give a credit limit"))
        self.assertEqual(risk.status, "refused")
        abstained, _ = self.pipeline(plan("ownership_relationships")).ask(AskRequest(question="Who is the beneficial owner?"))
        self.assertEqual(abstained.status, "abstained")

        bad_cypher = plan("incoming_ownership", targets=["LE-005"], cypher="MATCH (n:LegalEntity) RETURN n ORDER BY n.entity_uid LIMIT 1")
        guarded, _ = self.pipeline(bad_cypher, matches={"LE-005": [{"type": "LegalEntity", "canonical_id": "LE-005", "display_name": "Aqaba", "metadata": {}, "match_method": "exact"}]}).ask(AskRequest(question="Who owns LE-005?"))
        self.assertEqual(guarded.status, "abstained")

        unavailable = FakeOllama(plan("ownership_relationships"))
        unavailable.generate_cypher = lambda prompt: (_ for _ in ()).throw(ModelUnavailable())
        result, _ = AskPipeline(test_settings(), FakeGrounding(), FakeNeo4j(), unavailable, FakeDjango()).ask(AskRequest(question="List ownership relationships."))
        self.assertEqual(result.status, "unavailable")

        invalid = FakeOllama(plan("ownership_relationships"))
        invalid.generate_cypher = lambda prompt: (_ for _ in ()).throw(PlannerOutputError())
        django = FakeDjango()
        result, _ = AskPipeline(test_settings(), FakeGrounding(), FakeNeo4j(), invalid, django).ask(AskRequest(question="List ownership relationships."))
        self.assertEqual(result.status, "abstained")
        self.assertFalse(django.payloads[0]["cypher_executed"])

        with self.assertRaises(AuditUnavailable):
            self.pipeline(plan("ownership_relationships"), django=FakeDjango(AuditUnavailable())).ask(AskRequest(question="List ownership relationships."))
