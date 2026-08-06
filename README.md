# Watheeq Take-Home Assessment

## What Was Completed

This repository currently contains a limited project scaffold and verified local service startup. Business functionality has not been implemented.

Completed work:

- Reviewed the assessment requirements, supplied data, and schema registry.
- Verified the supplied assessment pack with `scripts/verify_pack.py` and committed `PACK_VERIFICATION.json`.
- Defined a deliberately limited implementation scope and planned architecture.
- Created the project file structure for the Django and FastAPI services.
- Added Docker Compose configuration for PostgreSQL, Django, Neo4j, Weaviate, FastAPI, and local Ollama.
- Added Django and FastAPI service scaffolds.
- Added `/health` and `/ready` endpoints for both Python services.
- Verified that the configured services were reachable through the Docker Compose network.
- Configured local Ollama settings for `qwen3:4b`.
- Configured Weaviate without a built-in vectorizer.

## What Was Not Completed

The scaffold does not yet implement the runtime data or question-answering path.

Not implemented:

- PostgreSQL domain models.
- Data ingestion or a functional `load_seed` command.
- Neo4j graph projection or a functional `project_graph` command.
- Projection reconciliation.
- Vector indexing, embedding generation, entity grounding, or question grounding.
- Ollama prompting.
- Cypher generation, Cypher guards, or Neo4j query execution.
- `/api/v1/ask` or other business endpoints.
- Answer generation, citations, or audit persistence.
- Monitoring, evaluation, business-path tests, integration tests, and end-to-end tests.

Deliberately excluded from the limited scope:

- Implementation and validation against the full 48-question evaluation set.
- Advanced beneficial-ownership calculations.
- Broad multi-hop graph reasoning.
- Domain-specific query support for assets, instruments, pledges, and filings.
- Automated conflict-resolution logic for contradictory and effective-dated records.

## Why These Items Were Not Completed

The assessment intentionally exceeds the available time. I prioritized a clear limited scope, an understandable architecture, a reproducible local environment, a working multi-service Docker Compose stack, verified connectivity, and honest documentation instead of presenting unverified business functionality as complete.

The detailed engineering choices and tradeoffs are recorded in [DECISIONS.md](DECISIONS.md).

## Core Project Structure

```text
django_service/
  Dockerfile
  manage.py
  requirements.txt
  registry/
  watheeq/
fastapi_service/
  Dockerfile
  requirements.txt
  app/
    clients/
tests/
  test_health.py
  test_guards.py
docker-compose.yml
.env.example
Makefile
```

The Python service directories currently contain framework scaffolding, health and readiness endpoints, and placeholder modules for future responsibilities. They do not contain business-path implementation.

`tests/test_guards.py` is currently a placeholder for the planned deterministic Cypher guard tests. The guards themselves are not implemented.

## Completed Infrastructure

The Docker Compose stack defines six services:

- PostgreSQL.
- Django with Django REST Framework.
- Neo4j.
- Weaviate.
- FastAPI.
- Local Ollama.

Named Docker volumes are configured for PostgreSQL, Neo4j, Weaviate, and Ollama. The services use Docker service names for internal networking.

## Planned Architecture

The following data path is planned and is not yet implemented:

```text
JSONL
  -> Django
  -> PostgreSQL
  -> Neo4j / Weaviate
```

The following question path is planned and is not yet implemented:

```text
User
  -> FastAPI
  -> Weaviate grounding
  -> Ollama qwen3:4b
  -> Cypher guard
  -> Neo4j
  -> deterministic answer
  -> Django audit
  -> PostgreSQL
```

FastAPI will communicate with Django through internal HTTP APIs rather than writing directly to PostgreSQL.

## Service Responsibilities

- PostgreSQL: planned system of record and audit storage.
- Django: planned data ingestion, PostgreSQL management, graph projection, and audit interface.
- Neo4j: planned rebuildable graph projection, written only by Django's `project_graph` command and queried read-only by FastAPI.
- Weaviate: planned entity and question grounding; no internal vectorization.
- Ollama: planned local Cypher generation using `qwen3:4b`.
- FastAPI: planned orchestration of the guarded query pipeline.

## Setup and Run

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Ollama model setup is separate:

```bash
docker compose exec ollama ollama pull qwen3:4b
docker compose exec ollama ollama list
```

The model is stored once in the Docker named volume and is not downloaded once per request.

For this verification, `docker compose exec -T ollama ollama list` confirmed that `qwen3:4b` is installed in the current local `ollama_data` volume. Fresh environments should run the model setup command above.

The verified local model digest is:

```text
359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7
```

Runtime requests identify the model as `qwen3:4b`; the digest is recorded separately for verification.

## Ports

- Django: `8000`
- FastAPI: `8001`
- PostgreSQL: `5432`
- Neo4j Browser: `7474`
- Neo4j Bolt: `7687`
- Weaviate: `8080`
- Ollama host port: `11435`
- Ollama internal Docker port: `11434`

## Health and Readiness Checks

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8001/ready
curl -i http://localhost:8080/v1/.well-known/ready
curl -fsS http://localhost:11435/api/tags
```

## Implemented Endpoints

- Django: `GET /health`, `GET /ready`.
- FastAPI: `GET /health`, `GET /ready`.

No business endpoints are implemented yet.

## Current Limitations

The repository currently verifies infrastructure startup and connectivity only. It does not ingest data, project a graph, generate or guard Cypher, index vectors, call Ollama for prompting, answer questions, return citations, or persist audit records.

Evaluation is not implemented. `EVAL_REPORT.md` has not been created because the assessment states that it must be generated by the evaluation harness.

## Related Documentation

- [AI_USE.md](AI_USE.md): AI-assistance record.
- [DECISIONS.md](DECISIONS.md): engineering and scope decisions.
- [SECURITY_NOTE.md](SECURITY_NOTE.md): current security posture and limitations.
- [AGENTS.md](AGENTS.md): rules for future AI coding assistants.

## Time Log

| Date                     | Time        |        Hours | Work completed                                                                                            |
| ------------------------ | ----------- | -----------: | --------------------------------------------------------------------------------------------------------- |
| Wednesday, 5 August 2026 | 07:00–10:00 |            3 | Reviewed the assessment, architecture, and project requirements                                           |
| Wednesday, 5 August 2026 | 17:00–19:00 |            2 | Reviewed the supplied data and schema and defined the initial implementation plan                         |
| Thursday, 6 August 2026  | 09:00–12:00 |            3 | Defined the limited-scope architecture, project structure, file responsibilities, and service connections |
| Thursday, 6 August 2026  | 12:00–16:00 |            4 | Implemented the service scaffold, Docker Compose stack, health checks, and connectivity verification      |
| **Total recorded time**  |             | **12 hours** | Assessment review, scope definition, architecture, infrastructure, and     |
