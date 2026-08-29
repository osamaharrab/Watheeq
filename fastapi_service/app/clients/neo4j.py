"""Small read-only Neo4j client for the ownership graph slice."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from neo4j import GraphDatabase, Query, READ_ACCESS
from neo4j.graph import Node, Path, Relationship
from neo4j.time import Date as Neo4jDate

from ..config import Settings


class GraphUnavailable(Exception):
    """Neo4j could not serve a read request."""


class QueryBoundedError(Exception):
    """A graph read exceeded its time or result bound."""


def _date_text(value: Any) -> str | None:
    """Convert projected temporal values to stable text for API-facing structures."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _serialize(value: Any) -> Any:
    """Convert Neo4j values into deterministic JSON-safe node, edge, and path shapes."""
    if isinstance(value, Neo4jDate):
        return value.iso_format()
    if isinstance(value, Node):
        return {
            "kind": "node",
            "labels": sorted(value.labels),
            "properties": {key: _serialize(value[key]) for key in sorted(value.keys())},
        }
    if isinstance(value, Relationship):
        return {
            "kind": "relationship",
            "type": value.type,
            "start": _serialize(value.start_node),
            "end": _serialize(value.end_node),
            "properties": {key: _serialize(value[key]) for key in sorted(value.keys())},
        }
    if isinstance(value, Path):
        return {
            "kind": "path",
            "nodes": [_serialize(node) for node in value.nodes],
            "relationships": [_serialize(relationship) for relationship in value.relationships],
        }
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(value[key]) for key in sorted(value)}
    return value


def _is_timeout(error: Exception) -> bool:
    message = str(error).lower()
    return "timeout" in message or "timed out" in message


class Neo4jClient:
    """Read supported ownership facts from the rebuildable Neo4j projection."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.driver = GraphDatabase.driver(
            settings.graph_db_uri,
            auth=(settings.graph_db_user, settings.graph_db_password),
        )

    def close(self) -> None:
        """Release the synchronous Neo4j driver when the process shuts down."""
        self.driver.close()

    def ready(self) -> bool:
        """Run a small read probe without allowing readiness failures to escape."""
        try:
            with self.driver.session(default_access_mode=READ_ACCESS) as session:
                return session.run("RETURN 1 AS ok").single()["ok"] == 1
        except Exception:
            return False

    def _run(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[Any]:
        """Execute one bounded read-only query and return raw Neo4j records."""
        try:
            with self.driver.session(default_access_mode=READ_ACCESS) as session:
                result = session.run(
                    Query(cypher, timeout=self.settings.query_timeout_seconds),
                    parameters or {},
                )
                records: list[Any] = []
                for record in result:
                    if len(records) >= self.settings.max_query_results:
                        raise QueryBoundedError("Neo4j result limit exceeded")
                    records.append(record)
                return records
        except QueryBoundedError:
            raise
        except Exception as error:
            if _is_timeout(error):
                raise QueryBoundedError("Neo4j query timed out") from error
            raise GraphUnavailable("Neo4j read failed") from error

    def execute_read(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run guarded Cypher and serialize every returned graph value safely."""
        return [
            {key: _serialize(record[key]) for key in sorted(record.keys())}
            for record in self._run(cypher, parameters)
        ]

    def resolve_exact(self, value: str) -> list[dict[str, Any]]:
        """Resolve exact typed IDs or names; display names are deliberately non-unique."""
        cypher = """
        MATCH (node)
        WHERE (node:LegalEntity AND (
            toLower(node.entity_uid) = toLower($value) OR
            toLower(node.legal_name) = toLower($value) OR
            toLower(coalesce(node.legal_name_ar, '')) = toLower($value)
        )) OR (node:NaturalPerson AND (
            toLower(node.person_uid) = toLower($value) OR
            toLower(node.full_name) = toLower($value) OR
            toLower(coalesce(node.full_name_ar, '')) = toLower($value)
        ))
        RETURN CASE WHEN node:LegalEntity THEN 'LegalEntity' ELSE 'NaturalPerson' END AS type,
               CASE WHEN node:LegalEntity THEN node.entity_uid ELSE node.person_uid END AS canonical_id,
               CASE WHEN node:LegalEntity THEN node.legal_name ELSE node.full_name END AS display_name,
               CASE WHEN node:LegalEntity
                    THEN {jurisdiction: node.jurisdiction, registration_no: node.registration_no}
                    ELSE {nationality: node.nationality}
               END AS metadata
        ORDER BY type, canonical_id
        """
        return [{**row, "match_method": "exact"} for row in self.execute_read(cypher, {"value": value})]

    def grounding_nodes(self) -> list[dict[str, Any]]:
        """Return only supported projected nodes for rebuilding grounding documents."""
        cypher = """
        MATCH (node)
        WHERE node:LegalEntity OR node:NaturalPerson
        RETURN CASE WHEN node:LegalEntity THEN 'LegalEntity' ELSE 'NaturalPerson' END AS type,
               CASE WHEN node:LegalEntity THEN node.entity_uid ELSE node.person_uid END AS canonical_id,
               CASE WHEN node:LegalEntity THEN node.legal_name ELSE node.full_name END AS display_name,
               CASE WHEN node:LegalEntity
                    THEN {jurisdiction: node.jurisdiction, registration_no: node.registration_no}
                    ELSE {nationality: node.nationality}
               END AS metadata
        ORDER BY type, canonical_id
        """
        return self.execute_read(cypher)

    def entity_exists(self, entity_uid: str) -> bool:
        """Check whether a LegalEntity exists in the ownership projection."""
        cypher = """
        MATCH (node:LegalEntity {entity_uid: $entity_uid})
        RETURN node.entity_uid AS entity_uid
        LIMIT 1
        """
        return bool(self.execute_read(cypher, {"entity_uid": entity_uid}))

    def ownership_paths(self, entity_uid: str, as_of: str | None) -> list[dict[str, Any]]:
        """Return bounded current or inclusive historical ownership paths for one entity."""
        if as_of is None:
            # valid_to=None means the ownership assertion is currently in force.
            temporal_where = "ALL(rel IN relationships(path) WHERE rel.valid_to IS NULL)"
            parameters = {"entity_uid": entity_uid}
        else:
            # Historical validity includes both dates: valid_from <= as_of <= valid_to.
            temporal_where = (
                "ALL(rel IN relationships(path) WHERE rel.valid_from <= date($as_of) AND "
                "(rel.valid_to IS NULL OR date($as_of) <= rel.valid_to))"
            )
            parameters = {"entity_uid": entity_uid, "as_of": as_of}
        cypher = f"""
        MATCH path=(holder)-[:HOLDS_INTEREST_IN*1..{self.settings.max_query_depth}]->
                   (target:LegalEntity {{entity_uid: $entity_uid}})
        WHERE (holder:LegalEntity OR holder:NaturalPerson)
          AND {temporal_where}
        RETURN path
        ORDER BY length(path),
                 [node IN nodes(path) |
                    CASE WHEN node:LegalEntity THEN node.entity_uid ELSE node.person_uid END]
        LIMIT {self.settings.max_query_results}
        """
        paths: list[dict[str, Any]] = []
        for record in self._run(cypher, parameters):
            path: Path = record["path"]
            paths.append(
                {
                    "nodes": [self._ownership_node(node) for node in path.nodes],
                    "relationships": [
                        self._ownership_relationship(path.nodes[index], path.nodes[index + 1], relationship)
                        for index, relationship in enumerate(path.relationships)
                    ],
                }
            )
        return paths

    @staticmethod
    def _ownership_node(node: Node) -> dict[str, str]:
        """Convert one projected node to the ownership endpoint's compact shape."""
        entity = "LegalEntity" in node.labels
        return {
            "type": "LegalEntity" if entity else "NaturalPerson",
            "canonical_id": str(node["entity_uid"] if entity else node["person_uid"]),
            "display_name": str(node["legal_name"] if entity else node["full_name"]),
        }

    @staticmethod
    def _ownership_relationship(holder: Node, held: Node, relationship: Relationship) -> dict[str, Any]:
        """Convert one graph edge while preserving bps, dates, and nullable filing UID."""
        holder_entity = "LegalEntity" in holder.labels
        return {
            "relationship": "HOLDS_INTEREST_IN",
            "holder_type": "LegalEntity" if holder_entity else "NaturalPerson",
            "holder_uid": str(holder["entity_uid"] if holder_entity else holder["person_uid"]),
            "held_entity_uid": str(held["entity_uid"]),
            "bps": int(relationship["bps"]),
            "valid_from": _date_text(relationship.get("valid_from")),
            "valid_to": _date_text(relationship.get("valid_to")),
            "filing_uid": (
                str(relationship.get("filing_uid"))
                if relationship.get("filing_uid") is not None
                else None
            ),
        }
