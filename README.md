# Watheeq Ownership Graph Slice

## What I implemented

- Django ingests the supplied seed data into PostgreSQL with source provenance.
- PostgreSQL is the authoritative record for the implemented data.
- Django projects the ownership slice into Neo4j and can reconcile that projection with PostgreSQL.
- Weaviate provides entity grounding and discovery.
- FastAPI serves the query API. It uses local Ollama `qwen3:4b` once to plan ownership intent and produce Text2Cypher.
- Generated Cypher is checked by deterministic read-only guards before Neo4j runs it.
- Final ownership answers are rendered deterministically from verified Neo4j relationship facts and citations. Every `/api/v1/ask` outcome is audited in PostgreSQL.
- An evaluation harness posts the supplied questions and records results in `EVAL_REPORT.md`.

## What I intentionally did not implement

The supplied registry is larger than this queryable slice. This project does not query or project asset control, instruments, unit holdings, pledges, filings as graph nodes, or other relationships outside ownership. It also does not support credit facilities, loan balances, sanctions or PEP status, valuation, risk scoring, credit scoring, lending decisions, or business recommendations.

## Why

I chose one complete ownership vertical slice instead of shallow support for the whole supplied registry. The implemented path covers ingestion, provenance, projection, reconciliation, grounding, guarded queries, citations, and audit for the same supported facts.

## Architecture

```text
Seed data
  -> Django ingestion
  -> PostgreSQL (authoritative)
  -> Neo4j projection (derived and rebuildable)
  -> reconciliation

Question
  -> policy and safety checks
  -> grounding and exact entity hints
  -> one local Ollama Text2Cypher planner call
  -> deterministic guard
  -> read-only Neo4j
  -> verified citations
  -> deterministic final response
  -> PostgreSQL audit
```

The queryable graph contains `LegalEntity` and `NaturalPerson` nodes with `HOLDS_INTEREST_IN` relationships. Relationships run from a natural person or legal entity to a legal entity and contain `bps`, `valid_from`, `valid_to`, and `filing_uid`.

`bps` is an integer: 10,000 bps equals 100 percent. There is no percentage property. Current ownership has `valid_to = null`. Historical ownership uses `valid_from <= as_of` and `(valid_to is null OR as_of <= valid_to)`; the end date is inclusive. Legal entities are identified by `entity_uid`, not legal name; natural persons are identified by `person_uid`.

## Requirements

- Docker and Docker Compose
- Enough local RAM and disk for the stack and the local `qwen3:4b` model

The base setup uses `docker-compose.yml`; no GPU is required. `docker-compose.gpu.yml` is optional local acceleration for an NVIDIA GPU.

## Quick start

From a fresh clone:

```bash
git clone <repository-url> Watheeq_Osama_Take_Home_Pack
cd Watheeq_Osama_Take_Home_Pack
cp .env.example .env
docker compose up --build -d
```

Pull the required local model, then check the model list:

```bash
docker compose exec -T ollama ollama pull qwen3:4b
curl -fsS http://localhost:11435/api/tags
```

Confirm that `qwen3:4b` has digest:

```text
359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7
```

Run the data and projection steps in this order:

```bash
docker compose exec -T django python manage.py migrate
docker compose run --rm --volume "$PWD/data:/app/data:ro" django \
  python manage.py load_seed --source data/graph_seed
docker compose exec -T django python manage.py project_graph
docker compose exec -T django python manage.py reconcile_projection
docker compose exec -T fastapi python scripts/rebuild_grounding.py
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8001/ready
```

The Django service does not mount `data/` by default. The explicit read-only mount in the `load_seed` command is required.

## API

`/api/v1/ask` currently supports only the `HOLDS_INTEREST_IN` ownership relationship slice. It supports current and structured historical ownership questions, outgoing holdings, and specific holder-to-company relationships. Requests outside that relationship scope are intended to return `unsupported`; the latest evaluation records remaining conservative classification errors.

Response statuses are: `answered` for verified ownership facts; `unsupported` for understood requests outside this slice; `abstained` for ownership requests that cannot be safely grounded, represented, or proved; `refused` for prohibited or unsafe requests; and `unavailable` when a required local dependency is unavailable.

```bash
curl -fsS http://localhost:8001/health | python -m json.tool
curl -fsS http://localhost:8001/ready | python -m json.tool
curl -fsS http://localhost:8001/api/v1/schema | python -m json.tool

curl -fsS -X POST http://localhost:8001/api/v1/entities/resolve \
  -H 'Content-Type: application/json' \
  -d '{"name":"Aqaba Logistics Park Company"}' | python -m json.tool

curl -fsS -X POST http://localhost:8001/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Who holds interests in LE-005?"}' | python -m json.tool

curl -fsS -X POST http://localhost:8001/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Which entities does NP-003 hold interests in?"}' | python -m json.tool

curl -fsS -X POST http://localhost:8001/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Does NP-003 hold an interest in LE-006?"}' | python -m json.tool

curl -fsS -X POST http://localhost:8001/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Who held interests in LE-005?","as_of":"2025-09-13"}' | python -m json.tool

curl -fsS -X POST http://localhost:8001/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"List all company names."}' | python -m json.tool

curl -fsS http://localhost:8000/api/v1/audit/<REQUEST_ID> | python -m json.tool
```

`/health` reports process liveness. `/ready` also checks the required local dependencies and the pinned Ollama model. `/api/v1/ask` returns its audit request ID in the `X-Request-ID` response header.

## Tests

```bash
docker compose run --rm --volume "$PWD/data:/app/data:ro" django \
  python manage.py test registry
docker compose exec -T fastapi python -m unittest discover -s tests
```

The Django command needs the same read-only seed-data mount. The latest developer-verified results were 42 Django tests passed and 61 FastAPI tests passed. Results may vary in a different environment.

## Evaluation

```bash
python scripts/run_eval.py
```

The harness posts 48 questions to `/api/v1/ask`, checks the expected outcome, validates citations independently, and checks that audit records were written. It keeps failures in the generated report.

The latest report records 21/48 passed outcome/citation/audit checks and 27 failures. Audit records were found for all 48 questions, and the unsupported assertion count was 0. No evaluation responses were scored as answered. Several failures were conservative abstentions or `unsupported` versus `abstained` classification mismatches; five evaluation requests returned `unavailable` because a required local dependency/runtime was unavailable. See [EVAL_REPORT.md](EVAL_REPORT.md) for the taxonomy and full results.

## Known limitations

- The queryable graph is intentionally limited to the ownership slice.
- Global ownership arithmetic and completeness assertions are intentionally not implemented.
- The local planner can be over-conservative: some supported ownership formulations abstain, and `unsupported` versus `abstained` classification is not yet perfect.
- Local model and dependency availability can affect latency and evaluation runs.

## Actual hours

Total actual development time: **43 hours**.

| Date | Time | Hours | Work completed |
| --- | --- | ---: | --- |
| 5 August 2026 | 07:00–10:00 | 3 | Reviewed the assessment, architecture, and project requirements |
| 5 August 2026 | 17:00–19:00 | 2 | Reviewed the supplied data and schema and defined the implementation plan |
| 6 August 2026 | 09:00–12:00 | 3 | Defined the project scope, architecture, structure, service responsibilities, and integration boundaries |
| 6 August 2026 | 12:00–16:00 | 4 | Implemented and verified the Docker Compose scaffold, health/readiness endpoints, and service connectivity |
| 22 August 2026 | — | 6 | Implemented, reviewed, and manually verified the Django/PostgreSQL data foundation |
| 24 August 2026 | — | 7 | Implemented and verified the PostgreSQL-to-Neo4j ownership projection, reconciliation, constraints, projection tests, and deliberate drift detection |
| 26 August 2026 | — | 4 | Continued implementation, debugging, and verification of the ownership query pipeline |
| 27 August 2026 | — | 6 | Worked on grounding, guarded query behaviour, evaluation fixes, testing, and verification |
| 28 August 2026 | — | 5 | Completed final correctness fixes, evaluation, repository cleanup, code comments, and submission documentation |
| 29 August 2026 | — | 3 | Final ownership-query validation, regression testing, evaluation review, and final documentation consistency work |
| **Total** |  | **43 hours** |  |

The recorded time covers the full development history represented in this repository, including implementation, debugging, testing, evaluation, verification, cleanup, and documentation.
