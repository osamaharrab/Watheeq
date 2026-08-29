"""The audited Text2Cypher route."""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Response

from ..clients.django import AuditUnavailable, DjangoClient
from ..clients.neo4j import Neo4jClient
from ..clients.ollama import OllamaClient
from ..clients.weaviate import WatheeqGrounding
from ..config import get_settings
from ..grounding import GroundingService, LocalEmbedder
from ..pipeline import AskPipeline
from ..schemas import AskRequest, AskResponse


router = APIRouter(prefix="/api/v1", tags=["ask"])


@lru_cache
def _pipeline() -> AskPipeline:
    """Create the long-lived local clients used by the audited ask route."""
    settings = get_settings()
    neo4j = Neo4jClient(settings)
    grounding = GroundingService(settings, neo4j, WatheeqGrounding(settings), LocalEmbedder(settings))
    return AskPipeline(settings, grounding, neo4j, OllamaClient(settings), DjangoClient(settings))


def get_pipeline() -> AskPipeline:
    """Provide the cached pipeline to FastAPI dependency injection."""
    return _pipeline()


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, response: Response, pipeline: AskPipeline = Depends(get_pipeline)) -> AskResponse:
    # Runs one audited question and returns its request ID in a response header.
    try:
        result, request_id = pipeline.ask(request)
    except AuditUnavailable as error:
        raise HTTPException(status_code=503, detail="Audit persistence is unavailable") from error
    # Keep request IDs out of the body so identical requests have deterministic bodies.
    response.headers["X-Request-ID"] = request_id
    return result
