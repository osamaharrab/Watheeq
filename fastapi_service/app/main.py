"""FastAPI application for the ownership query slice."""
from __future__ import annotations

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from .clients.django import DjangoClient
from .clients.neo4j import Neo4jClient
from .clients.ollama import OllamaClient
from .clients.weaviate import WatheeqGrounding
from .config import get_settings
from .routes.ask import router as ask_router
from .routes.entities import router as entities_router
from .routes.schema import router as schema_router


app = FastAPI(title="Watheeq ownership query service")
app.include_router(schema_router)
app.include_router(entities_router)
app.include_router(ask_router)


@app.middleware("http")
async def reject_oversized_body(request: Request, call_next):
    """Reject oversized requests while replaying validated bytes to the endpoint."""
    content_length = request.headers.get("content-length")
    limit = get_settings().max_request_body_bytes
    if content_length and (not content_length.isdigit() or int(content_length) > limit):
        return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
    # Content-Length is optional and client-controlled, so count received bytes too.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
    # Downstream FastAPI parsing still needs the body after this middleware consumes it.
    request._body = bytes(body)
    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    # Reports process liveness without probing dependencies.
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    # Reports whether every local dependency needed by the query service is ready.
    settings = get_settings()
    django = DjangoClient(settings)
    neo4j = Neo4jClient(settings)
    grounding = WatheeqGrounding(settings)
    ollama = OllamaClient(settings)
    # Readiness is stricter than health because it checks the full local pipeline.
    checks = {
        "django": django.readiness(),
        "neo4j": neo4j.ready(),
        "weaviate": grounding.ready(),
        "ollama": ollama.ready(),
    }
    django.close()
    neo4j.close()
    ollama.close()
    body = {"status": "ok" if all(checks.values()) else "unavailable", "checks": checks}
    if not all(checks.values()):
        return JSONResponse(status_code=503, content=body)
    return body
