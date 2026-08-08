# Watheeq Take-Home Assessment

## What I completed

- Reviewed the supplied assessment, data, and schema registry.
- Verified the supplied assessment pack.
- Defined a deliberately limited implementation scope.
- Created Django and FastAPI service scaffolds.
- Configured PostgreSQL, Django, Neo4j, Weaviate, FastAPI, and Ollama in Docker Compose.
- Implemented `/health` and `/ready` for Django and FastAPI.
- Verified the intended service connectivity during the recorded implementation work.
- Configured local Ollama with `qwen3:4b`.
- Configured Weaviate with internal vectorization and modules disabled.

The submitted application is an infrastructure scaffold. It does not implement business ingestion or question answering.

## What I did not complete

- PostgreSQL business-domain models and ingestion ledger
- functional `load_seed`
- `project_graph`
- `reconcile_projection`
- audit persistence and replay
- embedding generation
- Weaviate indexing
- entity and question grounding
- Text2Cypher
- deterministic Cypher guards
- bounded graph execution
- `/api/v1/ask`
- ownership and other business query endpoints
- deterministic cited answers
- complete abstention and refusal behavior
- 48-question evaluation harness
- `EVAL_REPORT.md`
- required complete automated test suite

## Why I scoped it this way

The brief is intentionally larger than the available time. I prioritized a small, verified infrastructure foundation over broad functionality that I could not verify properly.

The first planned business vertical slice would cover ownership questions only. It would prove one end-to-end path using `LegalEntity`, `NaturalPerson`, `HOLDS_INTEREST_IN`, ownership `bps`, `valid_from`, `valid_to`, and provenance. This ownership path is planned; it is not implemented in the current submission.

## Planned implementation structure

The placeholder modules below document the intended implementation boundaries. They do not implement the corresponding business functionality.

```text
django_service/registry/
├── ingestion.py
├── ownership.py
├── graph_projection.py
├── reconciliation.py
├── audit.py
└── planned_commands/
    ├── load_seed.py
    ├── project_graph.py
    ├── reconcile_projection.py
    └── replay_audit.py

fastapi_service/app/
  grounding.py
  schema_registry.py
  ownership.py
  pipeline.py
  guards.py
  clients/
  routes/

neo4j/
  constraints.cypher
```

| File | Planned responsibility |
| --- | --- |
| `registry/ingestion.py` | Supplied JSONL to provenance-preserving PostgreSQL records |
| `registry/ownership.py` | First ownership-domain processing slice |
| `registry/graph_projection.py` | PostgreSQL to Neo4j projection |
| `registry/reconciliation.py` | PostgreSQL/Neo4j drift detection |
| `registry/audit.py` | Immutable query audit ownership |
| `planned_commands/load_seed.py` | Future ingestion command boundary |
| `planned_commands/project_graph.py` | Future graph projection command boundary |
| `grounding.py` | Weaviate entity and question grounding |
| `schema_registry.py` | Allowed query-surface access |
| `guards.py` | Candidate Cypher validation |
| `pipeline.py` | Query-path orchestration |
| `clients/neo4j.py` | Planned read-only graph access |
| `clients/ollama.py` | Planned local Cypher generation |
| FastAPI `ownership.py` | Ownership query and result handling |

`planned_commands/` documents the required future Django management-command boundaries without registering non-functional commands with Django.

Using the supplied schema registry as authority, the first ownership mapping is:

```text
PLANNED — NOT IMPLEMENTED

NaturalPerson or LegalEntity
        |
        | HOLDS_INTEREST_IN
        | bps
        | valid_from
        | valid_to
        | filing_uid
        v
LegalEntity
```

### Planned ownership data flow

```text
PLANNED — NOT IMPLEMENTED

all supplied JSONL
    ->
Django ingestion
    ->
PostgreSQL ledger + provenance
    ->
ownership processing
    ->
graph projection
    ->
Neo4j derived ownership graph
```

All supplied records remain part of future ingestion accountability; ownership only limits the first supported business/query slice.

### Planned ownership query flow

```text
PLANNED — NOT IMPLEMENTED

ownership question
    ->
FastAPI
    ->
Weaviate grounding
    ->
schema registry
    ->
Ollama candidate Cypher
    ->
guards
    ->
read-only Neo4j
    ->
cited ownership result
    ->
Django audit
    ->
PostgreSQL
```

## Planned Weaviate design

Weaviate is planned for future entity and question grounding. Its internal vectorization and modules are disabled in the current infrastructure configuration.

The planned local embedding model is `all-MiniLM-L6-v2`, with 384-dimensional embeddings. The same model would generate stored vectors at index time and query vectors for dense retrieval. BM25 would not use embeddings. Planned hybrid retrieval would combine BM25 and dense retrieval with a default alpha of `0.5`.

Embedding generation, indexing, and retrieval are not implemented.

## Run the scaffold

Clone the repository and enter the project directory:

```bash
git clone https://github.com/osamaharrab/Watheeq.git
cd Watheeq
```

Create the runtime environment file and start the six services:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Pull the configured Ollama model into a fresh Ollama volume:

```bash
docker compose exec ollama ollama pull qwen3:4b
```

Setting `OLLAMA_MODEL=qwen3:4b` selects the model but does not install it. A fresh environment still needs the pull command above.

Verified model digest:

```text
359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7
```

Check the implemented health and readiness surfaces:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8001/ready
curl -i http://localhost:8080/v1/.well-known/ready
curl -fsS http://localhost:11435/api/tags
```

## Time spent

- Target time: 12 hours.
- Hard cap: 14 hours.
- Recorded assessment effort: 12 hours.

| Date                     | Time        | Hours | Work completed |
| ------------------------ | ----------- | ----: | -------------- |
| Wednesday, 5 August 2026 | 07:00–10:00 |     3 | Reviewed the assessment, architecture, and project requirements |
| Wednesday, 5 August 2026 | 17:00–19:00 |     2 | Reviewed the supplied data and schema and defined the implementation plan |
| Thursday, 6 August 2026  | 09:00–12:00 |     3 | Defined the limited scope, architecture, project structure, service responsibilities, and integration boundaries |
| Thursday, 6 August 2026  | 12:00–16:00 |     4 | Implemented and verified the Docker Compose scaffold, health/readiness endpoints, and service connectivity |
| **Total recorded time**  |             | **12 hours** | |
