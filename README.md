# Watheeq Take-Home Assessment

## What I completed

### Original submitted scaffold

- Reviewed the supplied assessment, data, and schema registry.
- Verified the supplied assessment pack.
- Defined a deliberately limited implementation scope.
- Created Django and FastAPI service scaffolds.
- Configured PostgreSQL, Django, Neo4j, Weaviate, FastAPI, and Ollama in Docker Compose.
- Implemented `/health` and `/ready` for Django and FastAPI.
- Verified the intended service connectivity during the recorded implementation work.
- Configured local Ollama with `qwen3:4b`.
- Configured Weaviate with internal vectorization and modules disabled.

The original timed submission was an infrastructure scaffold. It did not implement business ingestion or question answering.

### Post-submission continuation — 22 August 2026

Later continuation work implemented and manually verified the first Django/PostgreSQL data foundation:

- reviewed the assessment, supplied source data, authoritative schema, and existing scaffold;
- removed the temporary `django_service/registry/planned_commands/` directory and generated Python cache artifacts;
- implemented `IngestionRecord`, `LegalEntity`, `NaturalPerson`, `Filing`, and `OwnershipInterest`;
- implemented provenance-preserving ingestion for all 11 JSONL files and the first normalized `HOLDS_INTEREST_IN` ownership slice;
- implemented the real `registry/management/commands/load_seed.py` command;
- wrote 16 Django tests and generated `registry/migrations/0001_initial.py`;
- applied the migration, completed `python manage.py check` with no issues, and passed all 16 tests;
- loaded all 118 physical records: 117 accepted, 1 coerced, 0 quarantined, and 0 rejected;
- coerced `LE-023` dates from `11/03/2015` to `2015-03-11` and from `31/01/2026` to `2026-01-31`;
- ran `load_seed` a second time with identical accounting; and
- verified PostgreSQL counts of 118 ingestion records, 24 legal entities, 10 natural persons, 19 filings, and 29 ownership interests.

At that point, the graph projection and question-answering path remained unimplemented.

### Later post-submission continuation — 24 August 2026 — ownership graph projection and reconciliation

Later continuation work implemented and manually verified the first Neo4j ownership projection:

- implemented `graph_projection.py` and the `project_graph` management command;
- rebuilt the derived graph from authoritative PostgreSQL records before each projection;
- projected 24 `LegalEntity` nodes, 10 `NaturalPerson` nodes, and 29 `HOLDS_INTEREST_IN` relationships;
- added uniqueness constraints for `LegalEntity.entity_uid` and `NaturalPerson.person_uid`;
- ran `project_graph` twice with the same projection counts both times;
- passed the Django system check and all 19 Django tests, including 3 focused graph-projection tests; and
- visually inspected the projected ownership graph in Neo4j.

The same continuation later implemented and manually verified projection reconciliation for the ownership slice:

- implemented `reconciliation.py` and the `reconcile_projection` management command;
- compared `LegalEntity` and `NaturalPerson` identities and complete `HOLDS_INTEREST_IN` ownership facts rather than counts alone;
- added and passed 3 focused reconciliation tests, bringing the current Django test suite to 22 tests;
- introduced deliberate same-count ownership drift by changing one relationship's `bps` value and confirmed that reconciliation failed; and
- rebuilt Neo4j with `project_graph` and confirmed that reconciliation succeeded again.

### Later post-submission continuation — 25 August 2026 — schema registry foundation

This continuation adds the first runtime schema-registry boundary without expanding the graph:

- persists `watheeq-graph-1.0.0` in PostgreSQL as the schema registry version currently in force;
- implements `GET /api/v1/schema` in FastAPI;
- reads definitions from the single authoritative `reference/graph_schema_registry.json` file; and
- exposes only the verified ownership query surface: `LegalEntity`, `NaturalPerson`, and `HOLDS_INTEREST_IN`.

The endpoint does not expose the registry's other node labels or relationship types because they are not implemented in the running query path. Entity resolution, the ownership API, Text2Cypher, `/api/v1/ask`, audit, grounding, citations, and evaluation also remain unsupported.

## What I did not complete

- full audit persistence and `replay_audit`
- embedding generation
- Weaviate indexing and entity/question grounding
- guarded Text2Cypher
- deterministic Cypher guards
- bounded graph execution
- FastAPI entity and question endpoints
- `/api/v1/ask`
- deterministic cited answers
- complete abstention and refusal behavior
- 48-question evaluation harness
- `EVAL_REPORT.md`
- complete assessment-wide automated test coverage; 24 Django tests and 8 FastAPI tests currently cover the implemented data foundation, ownership projection, reconciliation, schema state, registry loading, and schema endpoint, but later required phases remain untested because they are not implemented

## Why I scoped it this way

The brief is intentionally larger than the available time. I prioritized a small, verified infrastructure foundation over broad functionality that I could not verify properly.

The later continuation implemented the PostgreSQL ingestion, normalized ownership records, rebuildable Neo4j ownership projection, and read-only projection reconciliation. Querying, citations, and audit remain planned.

## Implementation status and planned structure

The registry now contains the implemented data foundation alongside placeholders for later assessment responsibilities.

```text
django_service/registry/
├── models.py                                  IMPLEMENTED
├── ingestion.py                               IMPLEMENTED
├── ownership.py                               IMPLEMENTED
├── graph_projection.py                        IMPLEMENTED — OWNERSHIP SLICE
├── reconciliation.py                          IMPLEMENTED — OWNERSHIP SLICE
├── audit.py                                    PLANNED
└── management/commands/
    ├── load_seed.py                            IMPLEMENTED
    ├── project_graph.py                        IMPLEMENTED — OWNERSHIP SLICE
    └── reconcile_projection.py                 IMPLEMENTED — OWNERSHIP SLICE

Future management commands:
└── replay_audit                                 PLANNED

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

| File | Status and responsibility |
| --- | --- |
| `registry/models.py` | **Implemented:** schema version in force, ingestion ledger, entity/person/filing registries, and normalized ownership model |
| `registry/ingestion.py` | **Implemented:** provenance-preserving JSONL ingestion and accounting |
| `registry/ownership.py` | **Implemented:** first normalized ownership-domain slice |
| `registry/management/commands/load_seed.py` | **Implemented:** idempotent seed-loading command |
| `registry/graph_projection.py` | **Implemented for the ownership slice:** rebuilds Neo4j from PostgreSQL and projects legal entities, natural persons, and ownership relationships |
| `registry/reconciliation.py` | **Implemented for the ownership slice:** read-only PostgreSQL/Neo4j identity and ownership-fact comparison |
| `registry/audit.py` | **Planned:** immutable query-audit ownership |
| `project_graph` | **Implemented for the ownership slice:** rebuildable graph-projection management command |
| `reconcile_projection` | **Implemented for the ownership slice:** reports drift and exits non-zero without repairing it |
| `replay_audit` | **Planned:** audit-replay management command |
| `schema_registry.py` | **Implemented for the ownership slice:** loads the authoritative registry and selects the verified runtime query surface |
| `grounding.py`, `guards.py`, and `pipeline.py` | **Planned:** later FastAPI query-path responsibilities |

Using the supplied schema registry as authority, the first ownership mapping is:

```text
IMPLEMENTED IN POSTGRESQL, NEO4J, AND THE SCHEMA ENDPOINT

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

### Ownership data flow

```text
all supplied JSONL
    ->
Django ingestion                            IMPLEMENTED
    ->
PostgreSQL ledger + provenance              IMPLEMENTED
    ->
normalized ownership processing             IMPLEMENTED
    ->
ownership graph projection                  IMPLEMENTED
    ->
Neo4j derived ownership graph               IMPLEMENTED
```

### Projection reconciliation

```text
PostgreSQL authoritative ownership data
    ↓ compare
Neo4j derived ownership projection
```

`reconcile_projection` compares `LegalEntity` identities, `NaturalPerson` identities, and complete `HOLDS_INTEREST_IN` ownership facts. It is read-only: it reports drift but does not repair or synchronize either database. Manual verification changed one Neo4j relationship's `bps` value without changing the relationship count; reconciliation detected the mismatch, and a later explicit `project_graph` rebuild restored a successful comparison.

All supplied records now participate in ingestion accountability. Only entities, persons, filings, and ownership interests are normalized in this phase.

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

## Run the current scaffold, Django data foundation, and ownership projection

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

The current repository does not yet provide an end-to-end graph-query and AI-answering path.

Apply the checked-in Django migration and run the Django system check:

```bash
docker compose run --rm django python manage.py migrate
docker compose run --rm django python manage.py check
```

Run the 24 Django data-foundation, graph-projection, reconciliation, and schema-state tests:

```bash
docker compose run --rm \
  --volume "$PWD/data:/app/data:ro" \
  django python manage.py test registry.tests
```

Run the 8 focused FastAPI schema-registry and endpoint tests:

```bash
docker compose exec -T fastapi python -m unittest discover -s tests -v
```

Load the supplied seed data:

```bash
docker compose run --rm \
  --volume "$PWD/data:/app/data:ro" \
  django python manage.py load_seed --source data/graph_seed
```

`./data` is mounted read-only at `/app/data` because the Django image build context is `django_service/`.

Rebuild the derived Neo4j ownership projection from PostgreSQL:

```bash
docker compose run --rm django python manage.py project_graph
```

The manually verified projection contains 24 `LegalEntity` nodes, 10 `NaturalPerson` nodes, and 29 `HOLDS_INTEREST_IN` relationships. Running the command twice returned the same counts both times.

Compare the Neo4j ownership projection with authoritative PostgreSQL data:

```bash
docker compose exec -T django python manage.py reconcile_projection
```

The command was manually verified in a matching state, against deliberate same-count ownership drift, and again after rebuilding Neo4j with `project_graph`. It detects and reports drift but does not repair it automatically.

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
curl -fsS http://localhost:8001/api/v1/schema
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

### Post-submission development — 22 August 2026

Approximately 6 hours were spent implementing, reviewing, and manually verifying the Django/PostgreSQL data foundation. This was later continuation work and is not included in the original timed assessment total of 12 hours.

### Post-submission development — 24 August 2026

Approximately 7 hours were spent implementing and verifying the PostgreSQL-to-Neo4j ownership projection and reconciliation, including `project_graph`, Neo4j constraints, graph-projection tests, `reconcile_projection`, and deliberate drift detection. These 7 hours are post-submission continuation work and are not included in the original timed assessment total of 12 hours.
