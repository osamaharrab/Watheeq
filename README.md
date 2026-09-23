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
- Enough RAM and disk for the stack and `qwen2.5-coder:7b`
- CPU/base Compose is the default; GPU is optional

| Service | Purpose | Local address |
| --- | --- | --- |
| Django | authoritative ledger and audit API | `http://localhost:8000` |
| FastAPI | query/API service | `http://localhost:8001` |
| Neo4j | derived graph | `http://localhost:7474` |
| Weaviate | grounding index | `http://localhost:8080` |
| Ollama | local LLM | `http://localhost:11435` |
| Web console | Next.js analyst UI and same-origin BFF | `http://localhost:3000` |
| PostgreSQL | authoritative database | `localhost:5432` |

## Fresh-clone quick start

```bash
git clone \
  --branch feature-osama \
  --single-branch \
  https://github.com/osamaharrab/Watheeq.git \
  Watheeq

cd Watheeq_Osama

cp .env.example .env

docker compose up --build -d

docker compose exec -T ollama \
  ollama pull qwen2.5-coder:7b

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

Open **http://localhost:3000**.

Optional readiness check:

```bash
curl -fsS http://localhost:8000/ready | python -m json.tool
curl -fsS http://localhost:8001/ready | python -m json.tool
```

## Starting an already initialized environment

```bash
docker compose up -d
```

Open **http://localhost:3000**.

```

## Ollama placement

Ollama runs inside Docker Compose. This keeps model access on the Compose service network (`http://ollama:11434`) and makes the runtime path consistent across reviewer machines.

A host-installed Ollama was not chosen because `localhost` inside the FastAPI container refers to that container, not the host. Host Ollama would require host-specific routing and configuration, making model availability and digest verification less reproducible.

On a fresh Ollama volume, FastAPI `/ready` remains unavailable until the pinned model has been pulled (a quick start step). Runtime inference uses local Ollama; no hosted model API is used.

To verify the pinned model:

```bash
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

The quick start runs these steps in order: `migrate`, `load_seed`, `project_graph`, `reconcile_projection`, `rebuild_grounding.py`.

PostgreSQL is authoritative; Neo4j and Weaviate are rebuildable derived stores. The Django service does not mount `data/` by default, so the explicit read-only mount in the `load_seed` command is required. `reconcile_projection` exits non-zero if Neo4j does not match PostgreSQL.

## Verify readiness

`/health` checks process liveness. `/ready` checks required local dependencies. FastAPI readiness includes Django, Neo4j, Weaviate, and the pinned Ollama model.

```bash
curl -fsS http://localhost:8000/health | python -m json.tool
curl -fsS http://localhost:8001/health | python -m json.tool
```

The `/ready` checks are in the quick start.

## Frontend analyst console (`web/`)

### What was added

`web/` is a Next.js analyst console built on top of the existing backend. It calls the live FastAPI and Django services; it is not a mock frontend. No backend business logic or API contract was changed for it.

- **Entity Search** for companies (legal entities) and persons (natural persons). Ambiguous matches are never auto-selected.
- **Legal-entity ownership workspace:**
  - current ownership (no `as_of` sent)
  - historical ownership (exact `as_of` date)
  - direct owners and ownership chains
  - conflicts shown side by side
  - cycles and self-holdings flagged
  - ledger provenance (source file and line)
- **Ask Watheeq** for natural-language ownership questions:
  - evidence citations, each traceable to its ledger record
  - the audit record, fetched using the `X-Request-ID` response header
  - a separate state for each outcome: `answered`, `abstained`, `unsupported`, `refused`, `bounded_out`, `unavailable`
- **Service readiness indicator**, driven by both services' `/ready` endpoints.
- **Plain-language states.** Loading, empty and error states explain themselves in plain terms. Technical detail, including generated Cypher, stays behind collapsed disclosures.
- **Onboarding examples.** "Try an example" questions, each live-verified to return `answered`.
- **Responsive layout and accessibility.** Desktop, tablet and mobile layouts, with visible keyboard focus.

### Design

The screen structure and UI/UX direction were first designed in Figma. The three reference screens are stored in `docs/ui-reference/`. The design was then implemented by hand in Next.js and refined through testing against the live backend; Figma did not generate the frontend code.

The direction is deliberately restrained and analyst-focused:
- dark navy navigation and a light workspace
- clear hierarchy
- evidence-first interaction
- technical details disclosed only when asked for

### Architecture

```text
Browser
  -> Next.js :3000
       -> pages / UI
       -> server-side Route Handlers (BFF, /api/*)
            -> FastAPI (http://fastapi:8000)
            -> Django  (http://django:8000)
```

Browser code talks only to the same-origin Next.js `/api/*` routes. Next.js makes the server-side calls to FastAPI and Django. This meant backend CORS configuration did not need to change, and backend service URLs stay on the server. The browser never calls ports 8000 or 8001, and Django's `/internal/audit` write endpoint is never exposed.

### Why this frontend stack

- **Next.js (App Router).** React UI and server-side Route Handlers live in one project. That made the backend-for-frontend (BFF) pattern simple and let FastAPI and Django stay unchanged. Its standalone production build also fits the Docker Compose stack.
- **TypeScript.** Keeps the request and response contracts with FastAPI and Django explicit, which reduces integration mistakes.
- **Tailwind CSS.** Provides a small, consistent, responsive styling layer without a large UI framework.

Angular could also support this product. It would add more framework structure than this focused console needed, so the choice was based on scope and integration simplicity, not on Angular's capability.

### Compose integration

Inside Docker Compose, the `web` service reaches the backend over the Compose network:

```text
FASTAPI_BASE_URL=http://fastapi:8000
DJANGO_BASE_URL=http://django:8000
```

`web` receives only these two variables. It has no `env_file`, so no backend secrets reach it, and no `depends_on`, so it starts even when the backend is down and shows degraded or unavailable states.

See [web/README.md](web/README.md) for the BFF route table, UI behaviour, design and technology decisions, local development, verification, the future authentication design, and frontend limitations.

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
- Local inference latency depends on available hardware. In the web console, an Ask typically takes 1–3 minutes on CPU.
- `/ask` has no structured entity parameter, so the entity or person selected in the web console travels only in the question text.
- Authentication and authorization are intentionally deferred and are not implemented; there is no login and no JWT handling.
  - The existing backend does not expose an authentication or session contract for the frontend to use.
  - Frontend-only login or JWT handling would look like security without providing server-side authorization.
  - Authentication was therefore kept out of the frontend exercise and belongs to production hardening. [web/README.md](web/README.md) describes the intended design.

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

The 43 hours cover the original backend assessment work in this repository, including implementation, debugging, testing, evaluation, verification, cleanup, and documentation. The frontend follow-up is recorded separately below.

### Frontend follow-up (`web/`)

Total focused implementation time: approximately **7 hours**.

| Date | Time | Hours | Work completed |
| --- | --- | ---: | --- |
| 22 September 2026 | 19:00–22:00 | 3 | Reviewed the assignment requirements and the existing backend architecture and API behaviour. Planned the frontend architecture, the analyst user journey, and FastAPI/Django integration through a BFF without backend changes. Explored the UI/UX direction in Figma |
| 23 September 2026 | 11:00–15:00 | 4 | Refined the UI/UX design in Figma. Implemented the frontend in Next.js, TypeScript and Tailwind CSS: Entity Search, the Ownership workspace and Ask Watheeq, connected to the live FastAPI and Django services through the Next.js BFF. Implemented the evidence, citation, provenance, conflict and audit views. Tested current and historical ownership and live Ask queries, and refined the example questions. Improved usability, typography, responsiveness, accessibility, and error, empty and loading states. Ran tests, lint, typecheck, the production build and live integration checks |
| **Total** |  | **7 hours** |  |

Figma was used for UI/UX design and direction; the frontend implementation was written separately.
