# AI_USE.md

## Tools Used


I used Codex as the implementation assistant. Codex executed the specific instructions I gave it. It did not independently choose the final scope, architecture, service boundaries, or model.



The application does not currently prompt Ollama or generate Cypher.

## How Codex Was Used

Codex was used only as an implementation assistant. I defined the project scope, architecture, file structure, service responsibilities,  and implementation priorities. Codex executed the specific instructions I provided.

Codex helped with:

- Creating the requested Django and FastAPI scaffold.
- Creating the project directories and placeholder modules.
- Wiring imports, configuration, service URLs, and environment variables.
- Configuring Docker Compose for the required services.
- Adding the `/health` and `/ready` endpoints.
- Running verification commands.
- Formatting documentation from supplied facts.

Codex implemented the project modules and wired their imports, configuration, service URLs, environment variables, and Docker dependencies according to the structure and integration plan I had already defined.

## Human Decisions

I retained responsibility for the scope, architecture, file responsibilities, service boundaries, model selection, accepted changes, rejected changes, and final verification.

The decision to submit a smaller verified scaffold instead of broad unfinished business functionality was my decision.

## Corrections and Rejections

- I corrected the Weaviate configuration by adding `ENABLE_MODULES: ""` alongside `DEFAULT_VECTORIZER_MODULE: none`, so Weaviate stays configured for storage and search only.
- I replaced application-facing `NEO4J_*` variables with `GRAPH_DB_URI`, `GRAPH_DB_USER`, and `GRAPH_DB_PASSWORD`, because Neo4j treats the `NEO4J_*` namespace as server configuration.
- I changed the Ollama host port to `11435` while keeping the internal Docker URL as `http://ollama:11434`, because host port `11434` was unavailable.
- I rejected the idea that setting `OLLAMA_MODEL=qwen3:4b` installs the model. The model still has to be pulled into the Docker volume.
- I rejected any claim that placeholder modules implement ingestion, projection, guarding, auditing, or question answering.

## Verification

The scaffold was reviewed and verified locally with commands including:

```bash
python -m compileall django_service fastapi_service
docker compose config
docker compose up -d
docker compose ps
docker compose exec -T django python manage.py check
docker compose exec -T postgres pg_isready -U watheeq -d watheeq
docker compose exec -T neo4j cypher-shell -u neo4j -p '<configured-development-password>' "RETURN 1 AS ok"
docker compose exec -T ollama ollama list
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8001/ready
curl -i http://localhost:8080/v1/.well-known/ready
curl -fsS http://localhost:11435/api/tags
```

The Ollama digest was verified through the local Ollama tags API.

## Current Project State

Implemented infrastructure:

- Docker Compose configuration.
- PostgreSQL, Django, Neo4j, Weaviate, FastAPI, and Ollama services.
- Environment and service URL wiring.
- Health and readiness endpoints.
- Local service connectivity verification.
- Placeholder modules and documentation.

Not implemented:

- Data ingestion, persistence models, graph projection, reconciliation, embeddings, vector indexing, grounding, Ollama prompting, text-to-Cypher generation, Cypher validation, graph question answering, citations, audit persistence, refusals, abstentions, authentication, authorization, evaluation, or risk scoring.

Health and readiness endpoints are the only implemented HTTP functionality.
