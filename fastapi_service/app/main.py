import asyncio

import httpx
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase

from app.config import get_settings
from app.routes.schema import router as schema_router


app = FastAPI(title="Watheeq Query Service")
app.include_router(schema_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "fastapi"}


async def check_http(url: str, path: str):
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{url.rstrip('/')}{path}")
        if response.status_code < 400:
            return {"status": "ok"}
        return {"status": "unavailable", "status_code": response.status_code}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def check_neo4j():
    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.graph_db_uri,
        auth=(settings.graph_db_user, settings.graph_db_password),
    )
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run("RETURN 1").consume()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}
    finally:
        driver.close()


@app.get("/ready")
async def ready():
    settings = get_settings()
    dependencies = {
        "django": await check_http(settings.django_base_url, "/ready"),
        "neo4j": await asyncio.to_thread(check_neo4j),
        "weaviate": await check_http(settings.weaviate_url, "/v1/.well-known/ready"),
        "ollama": await check_http(settings.ollama_url, "/api/tags"),
    }
    is_ready = all(item["status"] == "ok" for item in dependencies.values())
    response_status = (
        status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=response_status,
        content={
            "status": "ready" if is_ready else "not_ready",
            "service": "fastapi",
            "dependencies": dependencies,
        },
    )
