"""Simple normalization for bounded ownership paths."""
from __future__ import annotations

from typing import Any


def ownership_citation_id(fact: dict[str, Any]) -> str:
    """Build a stable identifier for one effective-dated ownership assertion."""
    return ":".join(
        [
            "HOLDS_INTEREST_IN",
            fact["holder_type"],
            fact["holder_uid"],
            fact["held_entity_uid"],
            str(fact["bps"]),
            fact["valid_from"],
            str(fact["valid_to"]) if fact["valid_to"] is not None else "null",
            str(fact["filing_uid"]) if fact["filing_uid"] is not None else "null",
        ]
    )


def normalize_ownership(entity_uid: str, paths: list[dict[str, Any]], as_of: str | None) -> dict[str, Any]:
    """Shape bounded graph paths for the deterministic ownership endpoint."""
    normalized_paths: list[dict[str, Any]] = []
    direct_owners: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    for path in paths:
        # Keep every asserted edge; multiple same-day facts may be genuine conflicts.
        relationships = [{**relationship, "citation_id": ownership_citation_id(relationship)} for relationship in path["relationships"]]
        cycle = len({node["canonical_id"] for node in path["nodes"]}) != len(path["nodes"])
        normalized = {"nodes": path["nodes"], "relationships": relationships, "cycle": cycle}
        normalized_paths.append(normalized)
        facts.extend(relationships)
        if len(relationships) == 1:
            direct_owners.append(relationships[0])
    conflicts = _conflicts(facts)
    return {
        "entity_uid": entity_uid,
        "temporal_mode": "as_of" if as_of else "current",
        "as_of": as_of,
        "direct_owners": _unique_facts(direct_owners),
        "upstream_paths": normalized_paths,
        "conflict": bool(conflicts),
        "conflicts": conflicts,
        "message": "Ownership facts found." if paths else (
            "No ownership fact is available for the supplied as_of date." if as_of else
            "No current ownership fact is available. Supply as_of for historical ownership."
        ),
    }


def _unique_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove repeated direct facts while preserving stable citation order."""
    unique = {fact["citation_id"]: fact for fact in facts}
    return [unique[key] for key in sorted(unique)]


def _conflicts(facts: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Find incompatible assertions for the same holder and held entity."""
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for fact in facts:
        key = (fact["holder_uid"], fact["held_entity_uid"])
        grouped.setdefault(key, {})[fact["citation_id"]] = fact
    return [
        [facts_by_id[key] for key in sorted(facts_by_id)]
        for _, facts_by_id in sorted(grouped.items())
        if len(facts_by_id) > 1
    ]
