"""Straightforward synchronous orchestration for POST /api/v1/ask."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from .clients.django import DjangoClient
from .clients.neo4j import GraphUnavailable, Neo4jClient, QueryBoundedError
from .clients.ollama import ModelUnavailable, OllamaClient, PlannerOutputError
from .clients.weaviate import GroundingUnavailable
from .config import Settings
from .grounding import GroundingService
from .guards import CypherGuardError, validate_cypher
from .ownership import ownership_citation_id
from .schema_registry import get_queryable_schema
from .schemas import AskRequest, AskResponse, Citation, EntityMatch, Text2CypherOutput


_QUERY_KINDS = {
    "incoming_ownership",
    "outgoing_ownership",
    "relationship_check",
    "upstream_ownership",
    "ownership_relationships",
}

_OWNERSHIP_SCOPE_PATTERNS = (
    r"\b(?:owner|owners|owned|owns|owning|ownership)\b",
    r"\b(?:shareholder|shareholders|shareholdings?)\b",
    r"\b(?:holds?|held|holding)\s+(?:an?\s+)?(?:direct\s+)?interest(?:s)?\b",
    r"\binterest(?:s)?\s+(?:in|of)\b",
    r"\b(?:ownership\s+)?stakes?\b",
    r"\b(?:ownership\s+)?chain\b",
    r"\bupstream(?:\s+ownership)?\b",
    r"\bultimate\s+owners?\b",
    r"\bdirect\s+holders?\b",
    r"(?:ملكية|يملك|يملكون|مالك|ملاك|مساهم|حصة)",
)


class AskPipeline:
    """Run one guarded ownership plan and persist every final outcome."""

    def __init__(
        self,
        settings: Settings,
        grounding: GroundingService,
        neo4j: Neo4jClient,
        ollama: OllamaClient,
        django: DjangoClient,
    ):
        self.settings = settings
        self.grounding = grounding
        self.neo4j = neo4j
        self.ollama = ollama
        self.django = django

    def ask(self, request: AskRequest) -> tuple[AskResponse, str]:
        """Answer one ownership-relationship question and audit the final outcome."""
        request_id = str(uuid4())
        policy = _policy_outcome(request)
        if policy:
            return self._finish(request_id, request, *policy)

        try:
            schema = get_queryable_schema()
            exact_hints = _exact_planning_hints(self.grounding, request.question)
            plan = self.ollama.generate_cypher(
                _cypher_prompt(request, exact_hints, self.settings)
            )
            if plan.action == "unsupported":
                return self._finish(
                    request_id,
                    request,
                    "unsupported",
                    "This question is outside the currently supported ownership-relationship scope.",
                    [],
                    [],
                    [],
                    None,
                    False,
                    "outside ownership-relationship scope",
                )
            if plan.action == "abstain":
                return self._finish(
                    request_id,
                    request,
                    "abstained",
                    "The ownership question could not be represented safely.",
                    [],
                    [],
                    [],
                    None,
                    False,
                    plan.reason,
                )

            plan_error = _plan_error(plan)
            if plan_error:
                return self._finish(
                    request_id,
                    request,
                    "abstained",
                    "The ownership question could not be represented safely.",
                    [],
                    [],
                    [],
                    plan.cypher,
                    False,
                    plan_error,
                )

            entities, parameters, resolution_error = _resolve_plan_entities(
                self.grounding, plan, request.as_of
            )
            if resolution_error:
                return self._finish(
                    request_id,
                    request,
                    "abstained",
                    resolution_error,
                    [],
                    [],
                    [],
                    plan.cypher,
                    False,
                    resolution_error,
                )

            if not _plan_preserves_exact_hints(exact_hints, entities):
                return self._finish(
                    request_id,
                    request,
                    "abstained",
                    "The ownership query could not preserve all explicit entity references safely.",
                    [],
                    [],
                    [],
                    plan.cypher,
                    False,
                    "query plan omitted an explicit exact entity",
                )

            if not _cypher_matches_plan(plan, request, plan.cypher or ""):
                return self._finish(
                    request_id,
                    request,
                    "abstained",
                    "The ownership query plan did not match its declared relationship scope.",
                    entities,
                    [],
                    [],
                    plan.cypher,
                    False,
                    "query plan and Cypher do not match",
                )

            try:
                validate_cypher(
                    plan.cypher or "",
                    schema,
                    as_of=request.as_of.isoformat() if request.as_of else None,
                    max_depth=self.settings.max_query_depth,
                    max_results=self.settings.max_query_results,
                )
            except CypherGuardError as error:
                return self._finish(
                    request_id,
                    request,
                    "abstained",
                    f"Generated query was rejected: {error}",
                    entities,
                    [],
                    [],
                    plan.cypher,
                    False,
                    str(error),
                )

            rows = self.neo4j.execute_read(plan.cypher or "", parameters)
            citations = _citations(rows)
            if not citations:
                return self._finish(
                    request_id,
                    request,
                    "abstained",
                    "No citable ownership relationship was found for the supplied entities and date.",
                    entities,
                    [],
                    [],
                    plan.cypher,
                    True,
                    None,
                )

            conflicts = _citation_conflicts(citations)
            answer = _render_ownership_answer(request, plan, citations, conflicts)
            return self._finish(
                request_id,
                request,
                "answered",
                answer,
                entities,
                citations,
                conflicts,
                plan.cypher,
                True,
                None,
            )
        except QueryBoundedError:
            return self._finish(
                request_id,
                request,
                "bounded_out",
                "The graph query exceeded a configured safety bound.",
                [],
                [],
                [],
                None,
                False,
                "query bound",
            )
        except PlannerOutputError:
            return self._finish(
                request_id,
                request,
                "abstained",
                "The local ownership planner could not produce a valid safe plan.",
                [],
                [],
                [],
                None,
                False,
                "invalid planner output",
            )
        except (GraphUnavailable, GroundingUnavailable, ModelUnavailable):
            return self._finish(
                request_id,
                request,
                "unavailable",
                "A required local service is unavailable.",
                [],
                [],
                [],
                None,
                False,
                "dependency unavailable",
            )

    def _finish(
        self,
        request_id: str,
        request: AskRequest,
        status: str,
        answer: str,
        entities: list[dict[str, Any]],
        citations: list[Citation],
        conflicts: list[list[dict[str, Any]]],
        cypher: str | None,
        executed: bool,
        failure_reason: str | None,
    ) -> tuple[AskResponse, str]:
        """Build the response and fail closed if Django audit persistence fails."""
        response = AskResponse(
            status=status,
            answer=answer,
            resolved_entities=[
                EntityMatch.model_validate(entity) for entity in entities
            ],
            citations=citations,
            conflicts=conflicts,
        )
        schema = get_queryable_schema()
        payload = {
            "request_id": request_id,
            "question": request.question,
            "as_of": request.as_of.isoformat() if request.as_of else None,
            "generated_cypher": cypher,
            "cypher_executed": executed,
            "model_name": self.settings.ollama_model,
            "model_digest": self.settings.ollama_model_digest,
            "schema_version": schema.get(
                "schema_version", schema.get("version", "watheeq-graph-1.0.0")
            ),
            "resolved_entities": [
                entity.model_dump(mode="json") for entity in response.resolved_entities
            ],
            "citations": [citation.model_dump(mode="json") for citation in citations],
            "outcome": status,
            "final_response": response.model_dump(mode="json"),
            "failure_reason": failure_reason or "",
        }
        self.django.create_audit(payload)
        return response, request_id


def _policy_outcome(
    request: AskRequest,
) -> (
    tuple[
        str,
        str,
        list[dict[str, Any]],
        list[Citation],
        list[list[dict[str, Any]]],
        str | None,
        bool,
        str | None,
    ]
    | None
):
    """Keep deterministic checks for safety and ownership concepts with fixed meaning."""
    question = " ".join(request.question.casefold().split())
    if re.search(
        r"\b(create|merge|delete|detach|set|remove|drop|alter|call|load)\b", question
    ) or re.search(r"\b(?:ignore|bypass)\b(?:\s+\w+){0,3}\s+schema\b", question):
        return (
            "refused",
            "This service does not allow graph writes or schema-bypass requests.",
            [],
            [],
            [],
            None,
            False,
            "unsafe request",
        )
    if any(
        term in question
        for term in (
            "risk score",
            "credit limit",
            "default prediction",
            "approve lending",
            "decline lending",
            "riskiest counterparty",
            "rank counterpart",
        )
    ) or re.search(r"\b(?:most\s+)?likely\s+to\s+default\b", question):
        return (
            "refused",
            "This service does not score, rank, or make lending decisions.",
            [],
            [],
            [],
            None,
            False,
            "prohibited decision",
        )
    if (
        re.search(r"\bbeneficial\s+(?:owner|ownership)\b", question)
        or re.search(r"\bmore than one ownership chain\b", question)
        or re.search(r"\bcontrol(?:s|led|ling)?\b", question)
        or any(
            term in question
            for term in (
                "effective indirect interest",
                "economic interest",
            )
        )
    ):
        return (
            "abstained",
            "HOLDS_INTEREST_IN does not define that legal or business concept.",
            [],
            [],
            [],
            None,
            False,
            "undefined semantics",
        )
    if re.search(r"\b(?:everything|all)\s+associated\b", question):
        return _unsupported_outcome()
    if not _is_ownership_scope_question(question):
        return _unsupported_outcome()
    if request.as_of is None and re.search(r"\b(?:19|20)\d{2}\b", question):
        return (
            "abstained",
            "Supply structured as_of (YYYY-MM-DD) for historical ownership questions.",
            [],
            [],
            [],
            None,
            False,
            "missing structured as_of",
        )
    return None


def _unsupported_outcome() -> tuple[
    str,
    str,
    list[dict[str, Any]],
    list[Citation],
    list[list[dict[str, Any]]],
    str | None,
    bool,
    str | None,
]:
    return (
        "unsupported",
        "This question is outside the currently supported ownership-relationship scope.",
        [],
        [],
        [],
        None,
        False,
        "outside ownership-relationship scope",
    )


def _is_ownership_scope_question(question: str) -> bool:
    """Allow the local planner to handle only questions about ownership facts."""
    return any(
        re.search(pattern, question, re.IGNORECASE)
        for pattern in _OWNERSHIP_SCOPE_PATTERNS
    )


def _plan_error(plan: Text2CypherOutput) -> str | None:
    """Reject incomplete ownership plans instead of guessing how to repair them."""
    if plan.action != "query":
        return None
    if plan.query_kind not in _QUERY_KINDS or plan.answer_mode not in {
        "facts",
        "exists",
        "count",
    }:
        return "missing ownership query kind or answer mode"
    if not plan.cypher:
        return "missing generated Cypher"
    if any(
        not mention.strip()
        for mention in [*plan.holder_mentions, *plan.target_mentions]
    ):
        return "blank entity mention"

    required = {
        "incoming_ownership": (False, True),
        "outgoing_ownership": (True, False),
        "relationship_check": (True, True),
        "upstream_ownership": (False, True),
        "ownership_relationships": (False, False),
    }[plan.query_kind]
    needs_holders, needs_targets = required
    if (
        bool(plan.holder_mentions) != needs_holders
        or bool(plan.target_mentions) != needs_targets
    ):
        return "entity mentions do not match the ownership query kind"
    return None


def _resolve_plan_entities(
    grounding: GroundingService,
    plan: Text2CypherOutput,
    as_of: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any], str | None]:
    """Resolve only model-selected mentions and keep holder and target roles separate."""
    holder_entities, error = _resolve_mentions(
        grounding, plan.holder_mentions, "holder"
    )
    if error:
        return [], {}, error
    target_entities, error = _resolve_mentions(
        grounding, plan.target_mentions, "target"
    )
    if error:
        return [], {}, error

    entities = _unique_entities([*holder_entities, *target_entities])
    return (
        entities,
        {
            **(
                {
                    "holder_uids": sorted(
                        entity["canonical_id"] for entity in holder_entities
                    )
                }
                if holder_entities
                else {}
            ),
            **(
                {
                    "target_uids": sorted(
                        entity["canonical_id"] for entity in target_entities
                    )
                }
                if target_entities
                else {}
            ),
            **({"as_of": as_of} if as_of is not None else {}),
        },
        None,
    )


def _resolve_mentions(
    grounding: GroundingService, mentions: list[str], role: str
) -> tuple[list[dict[str, Any]], str | None]:
    entities: list[dict[str, Any]] = []
    for mention in mentions:
        matches = grounding.resolve_entity(mention)
        if len(matches) != 1:
            return [], "A required entity mention could not be resolved unambiguously."
        entity = matches[0]
        if role == "target" and entity["type"] != "LegalEntity":
            return [], "Ownership targets must resolve to a legal entity."
        if role == "holder" and entity["type"] not in {"LegalEntity", "NaturalPerson"}:
            return [], "Ownership holders must resolve to a supported entity."
        entities.append(entity)
    return _unique_entities(entities), None


def _unique_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep selected resolved entities in mention order without duplicate identities."""
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entity in entities:
        key = (entity["type"], entity["canonical_id"])
        if key not in seen:
            unique.append(entity)
            seen.add(key)
    return unique


def _exact_planning_hints(
    grounding: GroundingService, question: str
) -> list[dict[str, Any]]:
    """Keep only authoritative exact matches that occur in the user's question."""
    question_text = question.casefold()
    hints = []
    for entity in grounding.entity_candidates(question):
        if entity.get("match_method") != "exact":
            continue
        canonical_id = str(entity.get("canonical_id", "")).casefold()
        if not canonical_id:
            continue
        display_name = str(entity.get("display_name", "")).strip().casefold()
        if canonical_id in question_text or (
            display_name and display_name in question_text
        ):
            hints.append(entity)
    return _unique_entities(hints)


def _plan_preserves_exact_hints(
    exact_hints: list[dict[str, Any]], entities: list[dict[str, Any]]
) -> bool:
    """Do not execute a query when its plan silently drops an explicit endpoint."""
    selected = {(entity["type"], entity["canonical_id"]) for entity in entities}
    return all(
        (hint["type"], hint["canonical_id"]) in selected for hint in exact_hints
    )


def _cypher_matches_plan(
    plan: Text2CypherOutput, request: AskRequest, cypher: str
) -> bool:
    """Require the generated query to use the declared ownership roles and parameters."""
    parameters = set(re.findall(r"\$([A-Za-z_]\w*)", cypher))
    expected = {
        "incoming_ownership": {"target_uids"},
        "outgoing_ownership": {"holder_uids"},
        "relationship_check": {"holder_uids", "target_uids"},
        "upstream_ownership": {"target_uids"},
        "ownership_relationships": set(),
    }[plan.query_kind or "ownership_relationships"]
    if request.as_of is not None:
        expected.add("as_of")
    if parameters != expected:
        return False

    direct = not re.search(r"HOLDS_INTEREST_IN\s*\*", cypher, re.IGNORECASE)
    target_filter = bool(
        re.search(r"\btarget\.entity_uid\s+IN\s+\$target_uids\b", cypher, re.IGNORECASE)
    )
    holder_filters = all(
        re.search(pattern, cypher, re.IGNORECASE)
        for pattern in (
            r"\bholder\.entity_uid\s+IN\s+\$holder_uids\b",
            r"\bholder\.person_uid\s+IN\s+\$holder_uids\b",
        )
    )
    if plan.query_kind == "incoming_ownership":
        return direct and target_filter
    if plan.query_kind == "outgoing_ownership":
        return direct and holder_filters
    if plan.query_kind == "relationship_check":
        return direct and target_filter and holder_filters
    if plan.query_kind == "upstream_ownership":
        return not direct and target_filter
    return direct and "HOLDS_INTEREST_IN" in cypher.upper()


def _cypher_prompt(
    request: AskRequest,
    exact_hints: list[dict[str, Any]],
    settings: Settings,
) -> str:
    """Give the local model a small ownership-only plan and guarded Cypher surface."""
    temporal = (
        "AND rel.valid_to IS NULL"
        if request.as_of is None
        else "AND rel.valid_from <= $as_of\n  AND (rel.valid_to IS NULL OR $as_of <= rel.valid_to)"
    )
    path_temporal = (
        "ALL(rel IN relationships(path) WHERE rel.valid_to IS NULL)"
        if request.as_of is None
        else "ALL(rel IN relationships(path) WHERE rel.valid_from <= $as_of AND (rel.valid_to IS NULL OR $as_of <= rel.valid_to))"
    )
    holder_filter = """(holder:LegalEntity OR holder:NaturalPerson)
  AND (
       (holder:LegalEntity AND holder.entity_uid IN $holder_uids)
       OR
       (holder:NaturalPerson AND holder.person_uid IN $holder_uids)
      )"""
    order = "holder.entity_uid, holder.person_uid, target.entity_uid, rel.valid_from, rel.valid_to, rel.filing_uid, rel.bps"
    incoming = f"""MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity)
WHERE target.entity_uid IN $target_uids
  AND (holder:LegalEntity OR holder:NaturalPerson)
  {temporal}
RETURN holder, rel, target
ORDER BY {order}
LIMIT {settings.max_query_results}"""
    outgoing = f"""MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity)
WHERE {holder_filter}
  {temporal}
RETURN holder, rel, target
ORDER BY {order}
LIMIT {settings.max_query_results}"""
    relationship_check = f"""MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity)
WHERE {holder_filter}
  AND target.entity_uid IN $target_uids
  {temporal}
RETURN holder, rel, target
ORDER BY {order}
LIMIT {settings.max_query_results}"""
    upstream = f"""MATCH path=(holder)-[:HOLDS_INTEREST_IN*1..{settings.max_query_depth}]->(target:LegalEntity)
WHERE target.entity_uid IN $target_uids
  AND (holder:LegalEntity OR holder:NaturalPerson)
  AND {path_temporal}
RETURN path
ORDER BY length(path), elementId(holder)
LIMIT {settings.max_query_results}"""
    relationship_set = f"""MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target:LegalEntity)
WHERE (holder:LegalEntity OR holder:NaturalPerson)
  {temporal}
RETURN holder, rel, target
ORDER BY {order}
LIMIT {settings.max_query_results}"""
    hint_details = [
        {
            "type": entity["type"],
            "canonical_id": entity["canonical_id"],
            "display_name": entity["display_name"],
        }
        for entity in exact_hints
    ]

    return f"""Return JSON only:
{{"action":"query"|"unsupported"|"abstain","query_kind":"incoming_ownership"|"outgoing_ownership"|"relationship_check"|"upstream_ownership"|"ownership_relationships"|null,"answer_mode":"facts"|"exists"|"count"|null,"holder_mentions":[string],"target_mentions":[string],"cypher":string|null,"reason":string}}.

Planner contract:
- If action="query", query_kind MUST be a supported ownership query kind, answer_mode MUST be facts, exists, or count, and cypher MUST be non-null.
- NEVER return action="query" with query_kind=null, answer_mode=null, or cypher=null.
- If you cannot choose all required query fields safely, return action="abstain" instead.
- Before returning JSON, verify every action="query" has a non-null query_kind, answer_mode, and cypher.

Supported relationship only:
(LegalEntity or NaturalPerson)-[:HOLDS_INTEREST_IN]->(LegalEntity)
Facts available from it: holder identity, held legal-entity identity, bps, valid_from, valid_to, filing_uid, direct relationships, bounded upstream paths, and supported relationship counts.

Classify the requested information first. Use query only for those ownership facts or bounded upstream paths. Use unsupported for node properties, other labels or relationships, other business domains, schema questions, general graph exploration, or general chat. For unsupported use empty mentions and null cypher. Use abstain only for ownership questions that cannot be safely established: ambiguous identity, beneficial or legal-control concepts not defined here, indirect/economic calculations, completeness or missing-share arithmetic, missing structured historical date, or ambiguous ownership meaning.

Verified exact entity hints: {json.dumps(hint_details, sort_keys=True)}.
Hints identify entities; they do not make a non-ownership request supported. For one unambiguous exact hint, use its canonical_id directly in holder_mentions or target_mentions. If one written legal name maps to multiple exact hints, abstain. Otherwise use a literal concrete entity phrase and the application resolves it.

Query kinds:
- incoming_ownership: who holds an interest in named target(s); holder_mentions=[] and target_mentions contain target(s).
- outgoing_ownership: what named holder(s) hold interests in; holder_mentions contain holder(s) and target_mentions=[].
- relationship_check: a specific named holder-to-named target relationship; preserve both endpoints. Use it for stake, bps, existence, start date, or filing.
- upstream_ownership: bounded ownership chain from named target(s); target_mentions contain target(s).
- ownership_relationships: a request for the relationship set itself; both mention lists are empty.
Generic categories such as natural persons, people, legal entities, companies, and entities are type filters, never entity mentions. For an incoming type filter, use holder:NaturalPerson or holder:LegalEntity in Cypher.

Use facts for relationship facts, exists for positive relationship checks, and count for supported counts. Copy one supplied template. For outgoing_ownership and relationship_check, holders may be LegalEntity or NaturalPerson: preserve the complete typed holder filter from the supplied template, including both holder.entity_uid IN $holder_uids and holder.person_uid IN $holder_uids branches. Never simplify it to only one branch; copy the outgoing or relationship-check template structure exactly. Use only $holder_uids, $target_uids, and $as_of; never inline IDs, names, dates, or user values. Current ownership requires rel.valid_to IS NULL. Historical ownership uses the inclusive $as_of predicates in the template. Keep ORDER BY and the one literal LIMIT.

Examples: Target Beta -> LE-900 and Holder Alpha -> NP-900 are exact hints.
- "Who currently has an ownership interest in Target Beta?" => incoming_ownership, facts, holder_mentions=[], target_mentions=["LE-900"].
- "Which natural persons directly hold an interest in Target Beta?" => incoming_ownership, holder_mentions=[], target_mentions=["LE-900"], with holder:NaturalPerson.
- "Which entities does Holder Alpha currently hold interests in?" => outgoing_ownership, holder_mentions=["NP-900"], target_mentions=[].
- "What ownership stake does Holder Alpha hold in Target Beta?" => relationship_check, holder_mentions=["NP-900"], target_mentions=["LE-900"].
- "Trace the ultimate owners of Target Beta." => upstream_ownership, holder_mentions=[], target_mentions=["LE-900"].
- "What registry field is recorded for Target Beta?" => unsupported, empty mentions, cypher=null.

Incoming template:\n{incoming}

Outgoing template:\n{outgoing}

Relationship-check template:\n{relationship_check}

Upstream template:\n{upstream}

Ownership-relationship set template:\n{relationship_set}

User question: {request.question}
"""


def _citations(rows: list[dict[str, Any]]) -> list[Citation]:
    """Extract verified ownership facts in graph-result order for stable markers."""
    found: list[Citation] = []
    seen: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if (
                value.get("kind") == "relationship"
                and value.get("type") == "HOLDS_INTEREST_IN"
            ):
                start = value.get("start", {}).get("properties", {})
                end = value.get("end", {}).get("properties", {})
                properties = value.get("properties", {})
                holder_type = (
                    "LegalEntity" if start.get("entity_uid") else "NaturalPerson"
                )
                fact = {
                    "relationship": "HOLDS_INTEREST_IN",
                    "holder_type": holder_type,
                    "holder_uid": str(
                        start.get("entity_uid") or start.get("person_uid") or ""
                    ),
                    "held_entity_uid": str(end.get("entity_uid") or ""),
                    "bps": properties.get("bps"),
                    "valid_from": properties.get("valid_from"),
                    "valid_to": properties.get("valid_to"),
                    "filing_uid": properties.get("filing_uid"),
                }
                holder_name = start.get("legal_name") or start.get("full_name")
                held_entity_name = end.get("legal_name")
                if holder_name:
                    fact["holder_name"] = str(holder_name)
                if held_entity_name:
                    fact["held_entity_name"] = str(held_entity_name)
                if all(
                    fact[key] not in (None, "")
                    for key in ("holder_uid", "held_entity_uid", "bps", "valid_from")
                ):
                    citation_id = ownership_citation_id(fact)
                    if citation_id not in seen:
                        found.append(
                            Citation(
                                citation_id=citation_id,
                                kind="relationship",
                                details=fact,
                            )
                        )
                        seen.add(citation_id)
            for nested in value.values():
                visit(nested)

    visit(rows)
    return found


def _citation_conflicts(citations: list[Citation]) -> list[list[dict[str, Any]]]:
    """Group competing ownership assertions without resolving their disagreement."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for citation in citations:
        details = citation.details
        grouped.setdefault(
            (details["holder_uid"], details["held_entity_uid"]), []
        ).append({**details, "citation_id": citation.citation_id})
    return [
        facts
        for _, facts in sorted(grouped.items())
        if len({fact["citation_id"] for fact in facts}) > 1
    ]


def _render_ownership_answer(
    request: AskRequest,
    plan: Text2CypherOutput,
    citations: list[Citation],
    conflicts: list[list[dict[str, Any]]],
) -> str:
    """Render verified ownership facts so a marker can never move between facts."""
    # Rendering from citations prevents a language model from mismatching facts and markers.
    facts = [
        _render_relationship_fact(citation.details, index, plan.query_kind or "")
        for index, citation in enumerate(citations, start=1)
    ]
    if conflicts:
        date = f" as of {request.as_of.isoformat()}" if request.as_of else ""
        return (
            f"Conflicting ownership assertions are effective{date}: "
            + "; ".join(facts)
            + "."
        )

    joined = _join_facts(facts)
    if plan.answer_mode == "exists":
        return f"Yes. {joined}."
    if plan.answer_mode == "count":
        count, noun = _relationship_count(plan.query_kind or "", citations)
        return f"{count} {noun} found. {joined}."

    prefix = {
        "incoming_ownership": "Ownership relationships",
        "outgoing_ownership": "Outgoing ownership relationships",
        "relationship_check": "Verified ownership relationship",
        "upstream_ownership": "Upstream ownership relationships",
        "ownership_relationships": "Ownership relationships",
    }[plan.query_kind or "ownership_relationships"]
    if request.as_of:
        prefix += f" as of {request.as_of.isoformat()}"
    return f"{prefix}: {joined}."


def _render_relationship_fact(
    details: dict[str, Any], marker: int, query_kind: str
) -> str:
    holder = _entity_label(details.get("holder_name"), details["holder_uid"])
    target = _entity_label(details.get("held_entity_name"), details["held_entity_uid"])
    bps = details["bps"]
    if query_kind == "incoming_ownership":
        return f"{holder} ({bps} bps) [{marker}]"
    if query_kind == "outgoing_ownership":
        return f"{target} ({bps} bps) [{marker}]"
    fact = f"{holder} holds {bps} bps in {target}"
    if details.get("valid_from"):
        fact += f", effective from {details['valid_from']}"
    if details.get("valid_to"):
        fact += f" until {details['valid_to']}"
    if details.get("filing_uid"):
        fact += f" under filing {details['filing_uid']}"
    return f"{fact} [{marker}]"


def _entity_label(name: Any, identifier: str) -> str:
    return f"{name} ({identifier})" if name else identifier


def _join_facts(facts: list[str]) -> str:
    if len(facts) == 1:
        return facts[0]
    if len(facts) == 2:
        return f"{facts[0]} and {facts[1]}"
    return ", ".join(facts[:-1]) + f", and {facts[-1]}"


def _relationship_count(query_kind: str, citations: list[Citation]) -> tuple[int, str]:
    details = [citation.details for citation in citations]
    if query_kind == "incoming_ownership":
        return len({fact["holder_uid"] for fact in details}), "direct holder(s)"
    if query_kind == "outgoing_ownership":
        return len(
            {fact["held_entity_uid"] for fact in details}
        ), "held legal entity/entities"
    return len(details), "verified ownership relationship(s)"
