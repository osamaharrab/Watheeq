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

This continuation does not implement the graph projection or question-answering path.

## What I did not complete

- `project_graph`
- `reconcile_projection`
- full audit persistence and `replay_audit`
- embedding generation
- Weaviate indexing and entity/question grounding
- guarded Text2Cypher
- deterministic Cypher guards
- bounded graph execution
- FastAPI business endpoints
- `/api/v1/ask`
- deterministic cited answers
- complete abstention and refusal behavior
- 48-question evaluation harness
- `EVAL_REPORT.md`
- complete assessment-wide automated test suite; 16 tests currently cover only the Django data-foundation phase, while the assessment requires at least 18 across the completed system

## Why I scoped it this way

The brief is intentionally larger than the available time. I prioritized a small, verified infrastructure foundation over broad functionality that I could not verify properly.

The later continuation implemented the PostgreSQL ingestion and normalized ownership portion of that first vertical slice. Projection, querying, citations, and audit remain planned.

## Implementation status and planned structure

The registry now contains the implemented data foundation alongside placeholders for later assessment responsibilities.

```text
django_service/registry/
├── models.py                                  IMPLEMENTED
├── ingestion.py                               IMPLEMENTED
├── ownership.py                               IMPLEMENTED
├── graph_projection.py                        PLANNED
├── reconciliation.py                          PLANNED
├── audit.py                                    PLANNED
└── management/commands/
    └── load_seed.py                            IMPLEMENTED

Future management commands:
├── project_graph                               PLANNED
├── reconcile_projection                        PLANNED
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
| `registry/models.py` | **Implemented:** ingestion ledger, entity/person/filing registries, and normalized ownership model |
| `registry/ingestion.py` | **Implemented:** provenance-preserving JSONL ingestion and accounting |
| `registry/ownership.py` | **Implemented:** first normalized ownership-domain slice |
| `registry/management/commands/load_seed.py` | **Implemented:** idempotent seed-loading command |
| `registry/graph_projection.py` | **Planned:** PostgreSQL-to-Neo4j projection |
| `registry/reconciliation.py` | **Planned:** PostgreSQL/Neo4j drift detection |
| `registry/audit.py` | **Planned:** immutable query-audit ownership |
| `project_graph` | **Planned:** graph-projection management command |
| `reconcile_projection` | **Planned:** projection-reconciliation management command |
| `replay_audit` | **Planned:** audit-replay management command |
| `grounding.py`, `schema_registry.py`, `guards.py`, and `pipeline.py` | **Planned:** FastAPI query-path responsibilities |

Using the supplied schema registry as authority, the first ownership mapping is:

```text
IMPLEMENTED IN POSTGRESQL — NEO4J PROJECTION AND QUERYING REMAIN PLANNED

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
graph projection                            PLANNED
    ->
Neo4j derived ownership graph               PLANNED
```

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

## Run the current scaffold and Django data foundation

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

The current repository does not yet provide the unfinished graph-query and AI-answering path end to end.

Apply the checked-in Django migration and run the Django system check:

```bash
docker compose run --rm django python manage.py migrate
docker compose run --rm django python manage.py check
```

Run the 16 Django data-foundation tests:

```bash
docker compose run --rm \
  --volume "$PWD/data:/app/data:ro" \
  django python manage.py test registry.tests
```

Load the supplied seed data:

```bash
docker compose run --rm \
  --volume "$PWD/data:/app/data:ro" \
  django python manage.py load_seed --source data/graph_seed
```

`./data` is mounted read-only at `/app/data` because the Django image build context is `django_service/`.

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

### Post-submission development — 22 August 2026

Approximately 6 hours were spent implementing, reviewing, and manually verifying the Django/PostgreSQL data foundation. This was later continuation work and is not included in the original timed assessment total of 12 hours.
