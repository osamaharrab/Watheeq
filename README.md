# Watheeq Ownership Graph Slice

## What I implemented

- Django ingests the supplied seed data into PostgreSQL with source provenance.
- PostgreSQL is the authoritative record for the implemented data.
- Django projects the ownership slice into Neo4j and can reconcile that projection with PostgreSQL.
- Weaviate provides entity grounding and discovery.
- FastAPI serves the query API. It uses local Ollama `qwen2.5-coder:7b` once to plan ownership intent and produce Text2Cypher. No hosted model API is used at runtime.
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

## Supported graph surface

| Item | Implemented surface |
| --- | --- |
| Nodes | `LegalEntity`, `NaturalPerson` |
| Relationship | `HOLDS_INTEREST_IN` from a legal entity or natural person to a legal entity |
| Relationship properties | `bps`, `valid_from`, `valid_to`, `filing_uid` |
| Canonical identity | `entity_uid` for legal entities; `person_uid` for natural persons |

`bps` is an integer: 10,000 bps equals 100 percent. There is no percentage property. Current ownership has `valid_to = null`. Historical ownership uses `valid_from <= as_of` and `(valid_to is null OR as_of <= valid_to)`; the end date is inclusive. Legal entities are identified by `entity_uid`, not legal name; natural persons are identified by `person_uid`.

## Prerequisites

- Docker and Docker Compose
- Enough local RAM and disk for the stack and the local `qwen2.5-coder:7b` model

The default workflow uses CPU/base Docker Compose. No GPU is required.

| Service | Purpose | Local address |
| --- | --- | --- |
| Django | authoritative ledger and audit API | `http://localhost:8000` |
| FastAPI | query/API service | `http://localhost:8001` |
| Neo4j | derived graph | `http://localhost:7474` |
| Weaviate | grounding index | `http://localhost:8080` |
| Ollama | local LLM | `http://localhost:11435` |
| PostgreSQL | authoritative database | `localhost:5432` |

## Fresh-clone quick start

From a fresh clone:

```bash
git clone \
  --branch feature-osama \
  --single-branch \
  https://github.com/osamaharrab/Watheeq.git \
  Watheeq

cd Watheeq_Osama
cp .env.example .env
docker compose up --build -d
```

### Ollama placement

Ollama runs inside Docker Compose. This keeps model access on the Compose service network (`http://ollama:11434`) and makes the runtime path consistent across reviewer machines.

A host-installed Ollama was not chosen because `localhost` inside the FastAPI container refers to that container, not the host. Host Ollama would require host-specific routing and configuration, making model availability and digest verification less reproducible.

On a fresh Ollama volume, `docker compose up` starts the Ollama service, but FastAPI `/ready` remains unavailable until the pinned model is pulled. After the pull completes and the exact digest is present, the readiness check should succeed.

Pull the required local model, then check the model list. Runtime inference uses local Ollama; no hosted model API is used.

```bash
docker compose exec -T ollama \
  ollama pull qwen2.5-coder:7b
docker compose exec -T ollama ollama list

curl -fsS \
  http://localhost:11435/api/tags \
  | python -m json.tool
```

In the `qwen2.5-coder:7b` entry returned by `/api/tags`, verify this exact full digest. The shortened identifier shown by `ollama list` is not sufficient for full digest verification:

```text
dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364
```

## Initialize data and derived stores

Run these commands in order:

```bash
docker compose exec -T django \
  python manage.py migrate

docker compose run --rm \
  --volume "$PWD/data:/app/data:ro" \
  django \
  python manage.py load_seed --source data/graph_seed

docker compose exec -T django \
  python manage.py project_graph

docker compose exec -T django \
  python manage.py reconcile_projection

docker compose exec -T fastapi \
  python scripts/rebuild_grounding.py
```

PostgreSQL is authoritative; Neo4j and Weaviate are rebuildable derived stores. The Django service does not mount `data/` by default, so the explicit read-only mount in the `load_seed` command is required. `reconcile_projection` exits non-zero if Neo4j does not match PostgreSQL.

## Verify readiness

```bash
curl -fsS http://localhost:8000/health | python -m json.tool
curl -fsS http://localhost:8000/ready  | python -m json.tool

curl -fsS http://localhost:8001/health | python -m json.tool
curl -fsS http://localhost:8001/ready  | python -m json.tool
```

`/health` checks process liveness. `/ready` checks required local dependencies. FastAPI readiness includes Django, Neo4j, Weaviate, and the pinned Ollama model.

## API walkthrough

`/api/v1/ask` supports only the `HOLDS_INTEREST_IN` ownership relationship slice. `answered` responses require verified ownership facts and citations. Understood requests outside the slice are `unsupported`; ownership requests that cannot be safely grounded, represented, or proved are `abstained`; unsafe requests are `refused`.

| Method | Endpoint | Service |
| --- | --- | --- |
| POST | `/api/v1/ask` | FastAPI |
| POST | `/api/v1/entities/resolve` | FastAPI |
| GET | `/api/v1/entities/{entity_uid}/ownership` | FastAPI |
| GET | `/api/v1/schema` | FastAPI |
| GET | `/api/v1/audit/{request_id}` | Django |
| GET | `/api/v1/ledger/entities/{entity_uid}` | Django |
| GET | `/health` and `/ready` | both services |

Schema:

```bash
curl -fsS \
  http://localhost:8001/api/v1/schema \
  | python -m json.tool
```

Entity resolution:

```bash
curl -fsS -X POST \
  http://localhost:8001/api/v1/entities/resolve \
  -H 'Content-Type: application/json' \
  -d '{"name":"Aqaba Logistics Park Company"}' \
  | python -m json.tool
```

Known successful natural-language ownership query:

```bash
curl -fsS -X POST \
  http://localhost:8001/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Who holds interests in LE-005?"}' \
  | python -m json.tool
```

Deterministic current and historical ownership endpoints:

```bash
curl -fsS \
  http://localhost:8001/api/v1/entities/LE-005/ownership \
  | python -m json.tool

curl -fsS \
  "http://localhost:8001/api/v1/entities/LE-005/ownership?as_of=2025-09-13" \
  | python -m json.tool
```

PostgreSQL ledger and provenance view:

```bash
curl -fsS \
  http://localhost:8000/api/v1/ledger/entities/LE-005 \
  | python -m json.tool
```

## Required Django management commands

The initialization section uses `load_seed`, `project_graph`, and `reconcile_projection`. To replay an audited request from its immutable audit row:

```bash
docker compose exec -T django \
  python manage.py replay_audit --request-id <REQUEST_ID>
```

`replay_audit` reconstructs the recorded request from the immutable audit row without relying on the original conversation.

## Audit and replay

`/api/v1/ask` returns its audit request ID in the `X-Request-ID` response header. Retrieve it through Django, then use the replay command above if needed.

```bash
curl -fsS \
  http://localhost:8000/api/v1/audit/<REQUEST_ID> \
  | python -m json.tool
```

The generated [EVAL_REPORT.md](EVAL_REPORT.md) includes separate live smoke-test examples for a successful query, abstention, refusal, and conflict. Those examples are not counted in the 48-question evaluation metrics.

## Tests

```bash
docker compose run --rm \
  --volume "$PWD/data:/app/data:ro" \
  django \
  python manage.py test registry

docker compose exec -T fastapi \
  python -m unittest discover -s tests
```

The Django command needs the same read-only seed-data mount. The test suite is designed to run without hosted-model or network inference.

## Evaluation

```bash
python scripts/run_eval.py
```

The harness posts the 48 supplied questions to `/api/v1/ask`, checks expected outcomes, validates citations independently, checks Django audit rows, and applies fixture-backed oracles where defensible. It generates `EVAL_REPORT.md` and retains failures.

The current report records **42/48 evaluation cases passed the outcome/citation/audit harness checks**, with 6 failures. This is not 87.5% ownership-answer accuracy: 1/4 expected `answered` cases passed, while 26/28 expected `unsupported`, 10/11 expected `abstained`, and 5/5 expected `refused` cases passed. Audit coverage was 48/48, unsupported assertions remained 0, and the one answered evaluation case passed its oracle and citation validation.

Direct ownership is 1/2 in the report; ownership traversal remains 0/2. Several supported formulations still abstain. See [EVAL_REPORT.md](EVAL_REPORT.md) for all six failures, per-class results, and the four live smoke-test examples.

## Pack verification

```bash
python scripts/verify_pack.py
```

This writes the supplied-fixture verification record to `PACK_VERIFICATION.json`. Do not edit that record by hand.

## Optional GPU acceleration

`docker-compose.gpu.yml` is optional NVIDIA acceleration only. The CPU/base workflow above is the normal reviewer path.

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  up -d --build
```

## Known limitations

- The queryable graph is intentionally limited to the ownership slice.
- Global ownership arithmetic and completeness assertions are not fully supported.
- Some valid supported ownership formulations still abstain; traversal remains weak.
- `unsupported` versus `abstained` routing is not perfect.
- Generated plans fail closed when they do not match deterministic validation; they are not silently repaired.
- Local inference latency depends on available hardware.

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
