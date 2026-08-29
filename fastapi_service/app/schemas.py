"""Public FastAPI request and response contracts."""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import DEFAULT_MAX_QUESTION_CHARS


class SchemaResponse(BaseModel):
    # Describes the registry-derived graph surface exposed by the running API.
    schema_version: str
    node_labels: dict[str, list[str]]
    relationship_types: dict[str, dict[str, Any]]
    not_represented: list[str] = Field(default_factory=list)


class EntityResolveRequest(BaseModel):
    # Accepts one entity name or canonical identifier for resolution.
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=300)


class EntityMatch(BaseModel):
    # Represents one typed entity candidate with its resolution method.
    type: Literal["LegalEntity", "NaturalPerson"]
    canonical_id: str
    display_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    match_method: Literal["exact", "hybrid"]


class EntityResolveResponse(BaseModel):
    # Returns zero, one, or many typed entity matches without guessing.
    matches: list[EntityMatch] = Field(default_factory=list)


class AskRequest(BaseModel):
    # Accepts a bounded question and optional structured historical date.
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=DEFAULT_MAX_QUESTION_CHARS)
    as_of: date | None = None


class Citation(BaseModel):
    # References one verified node or ownership fact used by an answer.
    citation_id: str
    kind: Literal["node", "relationship"]
    details: dict[str, Any]


class AskResponse(BaseModel):
    # Returns the audited answer outcome with verified citations and conflicts.
    status: Literal["answered", "unsupported", "abstained", "refused", "bounded_out", "unavailable"]
    answer: str
    resolved_entities: list[EntityMatch] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    conflicts: list[list[dict[str, Any]]] = Field(default_factory=list)


class OwnershipFact(BaseModel):
    # Represents one HOLDS_INTEREST_IN assertion using integer basis points.
    relationship: Literal["HOLDS_INTEREST_IN"]
    holder_type: Literal["LegalEntity", "NaturalPerson"]
    holder_uid: str
    held_entity_uid: str
    bps: int
    valid_from: str
    valid_to: str | None
    filing_uid: str | None
    citation_id: str


class OwnershipPath(BaseModel):
    # Represents one bounded upstream ownership path and any detected cycle.
    nodes: list[dict[str, str]]
    relationships: list[OwnershipFact]
    cycle: bool = False


class OwnershipResponse(BaseModel):
    # Returns deterministic current or as-of ownership facts for one entity.
    entity_uid: str
    temporal_mode: Literal["current", "as_of"]
    as_of: date | None = None
    direct_owners: list[OwnershipFact] = Field(default_factory=list)
    upstream_paths: list[OwnershipPath] = Field(default_factory=list)
    conflict: bool = False
    conflicts: list[list[OwnershipFact]] = Field(default_factory=list)
    message: str


class Text2CypherOutput(BaseModel):
    # Constrains one local ownership plan before it reaches the deterministic guard.
    model_config = ConfigDict(extra="forbid")
    action: Literal["query", "unsupported", "abstain"]
    query_kind: Literal[
        "incoming_ownership",
        "outgoing_ownership",
        "relationship_check",
        "upstream_ownership",
        "ownership_relationships",
    ] | None = None
    answer_mode: Literal["facts", "exists", "count"] | None = None
    holder_mentions: list[str] = Field(default_factory=list)
    target_mentions: list[str] = Field(default_factory=list)
    cypher: str | None = None
    reason: str
