"""Entity resolution and deterministic ownership routes."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from ..clients.neo4j import GraphUnavailable, Neo4jClient, QueryBoundedError
from ..clients.weaviate import WatheeqGrounding
from ..config import get_settings
from ..grounding import GroundingService, LocalEmbedder
from ..ownership import normalize_ownership
from ..schemas import EntityMatch, EntityResolveRequest, EntityResolveResponse, OwnershipResponse


router = APIRouter(prefix="/api/v1/entities", tags=["entities"])


@lru_cache
def _grounding_service() -> GroundingService:
    """Create the cached entity-grounding service for resolution requests."""
    settings = get_settings()
    return GroundingService(settings, Neo4jClient(settings), WatheeqGrounding(settings), LocalEmbedder(settings))


@lru_cache
def _neo4j_client() -> Neo4jClient:
    """Create the cached read-only graph client for ownership lookups."""
    return Neo4jClient(get_settings())


def get_grounding() -> GroundingService:
    """Provide entity grounding through FastAPI dependency injection."""
    return _grounding_service()


def get_neo4j() -> Neo4jClient:
    """Provide the read-only graph client through FastAPI dependency injection."""
    return _neo4j_client()


@router.post("/resolve", response_model=EntityResolveResponse)
def resolve_entity(request: EntityResolveRequest, grounding: GroundingService = Depends(get_grounding)) -> EntityResolveResponse:
    # Resolves an exact supported identity before falling back to hybrid discovery.
    return EntityResolveResponse(matches=[EntityMatch.model_validate(match) for match in grounding.resolve_entity(request.name)])


@router.get("/{entity_uid}/ownership", response_model=OwnershipResponse)
def ownership(
    entity_uid: str,
    as_of: date | None = None,
    neo4j: Neo4jClient = Depends(get_neo4j),
) -> OwnershipResponse:
    # Returns deterministic current or inclusive historical ownership facts.
    if not neo4j.entity_exists(entity_uid):
        raise HTTPException(status_code=404, detail="LegalEntity not found")
    try:
        as_of_text = as_of.isoformat() if as_of else None
        return OwnershipResponse.model_validate(
            normalize_ownership(entity_uid, neo4j.ownership_paths(entity_uid, as_of_text), as_of_text)
        )
    except QueryBoundedError as error:
        raise HTTPException(status_code=503, detail="Ownership query exceeded a safety bound") from error
    except GraphUnavailable as error:
        raise HTTPException(status_code=503, detail="Neo4j is unavailable") from error
