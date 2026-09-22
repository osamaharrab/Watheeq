# Watheeq Take-Home Assessment

## Osama Al-Harrab: Corporate Graph Service with Guarded Query Generation

**Issued:** Tuesday, 4 August 2026
**Deadline:** Thursday, 6 August 2026, 23:59 Amman time
**Target effort:** 12 hours. Hard cap 14 hours.
**Stack:** Python 3.11+, Django 4.2+ with Django REST Framework, PostgreSQL, FastAPI, Neo4j, a
vector store of your choice, Docker Compose, and a locally hosted language model served by Ollama.

---

## 1. What this assessment is for

Watheeq assesses entities whose ownership, control and asset structures are recorded across
inconsistent sources. The question "who actually stands behind this counterparty, as at a given
date" is the load-bearing one, and it is a graph question.

We are not measuring whether you can wire up a retrieval service. We assume you can. We are
measuring what your service does when the graph disagrees with itself, when a question cannot be
answered from the schema, and when the data itself is hostile.

Assume nothing in the supplied data is clean. Assume nothing in this brief is complete.

---

## 2. Rules

- **LLM use is permitted and expected** for building this. You are accountable for every submitted
  line and must be able to explain, modify and test it without the original conversation in front
  of you.
- **No public inference API.** The service must not call OpenAI, Anthropic, xAI, Google or any
  hosted model at runtime. Runtime inference is served by a local model through Ollama. Pin the
  model by name and digest.
- **Everything runs under Docker Compose** and must come up from a cold `docker compose up` on a
  machine that has never seen your project. Tests run with the network disabled.
- **Time.** Target 12 hours, hard cap 14, inside a two day window. **You are not expected to
  finish everything in this brief.** That is deliberate. What you choose to build first, what you
  choose to leave, and how clearly you say so is the point of the exercise. A small, correct,
  well argued piece of work with an honest account of what was left undone scores higher than a
  complete-looking submission you have not verified. Open your README with what you did, what you
  did not, and why in that order. Record your actual hours honestly.
- **Commits.** Private Git repository plus a ZIP export. At least eight meaningful commits. A
  single large commit is treated as an absence of working history.
- **Ask.** If something in this brief is unclear, wrong, or cannot be satisfied as written, email
  Big. Asking is measured on the same footing as the code.

### Required AI-use record

`AI_USE.md` must state the tools and models used, which components received substantial assistance,
at least two suggestions you rejected or materially corrected with the reason and the evidence you
used to verify, and where you relied on your own judgement instead of generated output.

---

## 3. Supplied material

| Path | Contents |
| --- | --- |
| `data/graph_seed/` | Eleven JSONL files of entities, persons, filings, interests, assets, instruments, pledges and holdings. |
| `reference/graph_schema_registry.json` | The authoritative description of the queryable surface. |
| `data/eval/eval_questions.jsonl` | 48 questions, with identifiers only. No expected answers. |
| `templates/` | Templates you must complete. |
| `scripts/verify_pack.py` | Verifies you are working from the correct fixtures. Run it and commit the output. |

The seed records are synthetic. They were produced by Watheeq for this assessment. No entity,
person, asset or instrument in them is real.

---

## 4. The build

### Architecture

Two applications, one system.

**Django plus PostgreSQL is the system of record.** Every supplied record lands there first, with
its provenance. Django owns the ingestion ledger, the entity and filing registry, the schema
registry version in force, and an immutable audit log of every question the system is asked.

**Neo4j is a derived projection.** It is rebuildable from PostgreSQL at any time and it is never
written to by anything other than the projection command. If the two disagree, PostgreSQL is right
and the projection is broken.

**FastAPI serves the query path.** It reads the graph, generates guarded Cypher, and writes an
audit record back to Django for every request including the ones it refuses.

Follow Watheeq's domain-driven module naming. Django apps are named for the domain they own, not
for their layer.

### Required services

A single `docker compose up` brings up: PostgreSQL, your Django application, Neo4j, your vector
store, your FastAPI application, and any supporting service. It must come up in the right order,
from a cold start, on a machine that has never seen your project.

The local model is served by Ollama. Whether Ollama runs inside the compose project or on the host
is your decision, and you must document why you chose what you chose and what the failure mode of
the other option is. Choose a model small enough to run on CPU on a developer laptop. Pin it by
name and digest. State the exact pull command.

### Required Django management commands

```bash
python manage.py migrate
python manage.py load_seed --source data/graph_seed
python manage.py project_graph
python manage.py reconcile_projection
python manage.py replay_audit --request-id <id>
```

- `load_seed` writes the supplied records into PostgreSQL with provenance. Idempotent. It reports
  what it accepted, what it coerced and what it rejected, and it does not silently drop anything.
- `project_graph` rebuilds Neo4j from PostgreSQL. Idempotent. Safe to run against a populated
  graph.
- `reconcile_projection` proves the graph matches the ledger and exits non-zero if it does not.
  What "matches" means is your definition and you will be asked to defend it.
- `replay_audit` reconstructs what happened for a given request from the audit log alone.

### Required endpoints

| Method | Path | Served by | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/ask` | FastAPI | Natural language question against the graph. |
| `POST` | `/api/v1/entities/resolve` | FastAPI | Resolve a name or identifier to zero, one or many entities. |
| `GET` | `/api/v1/entities/{entity_uid}/ownership` | FastAPI | Ownership structure, as-of a supplied date. |
| `GET` | `/api/v1/schema` | FastAPI | The queryable surface actually exposed by the running service. |
| `GET` | `/api/v1/audit/{request_id}` | Django REST Framework | The full audit record for one request. |
| `GET` | `/api/v1/ledger/entities/{entity_uid}` | Django REST Framework | The record of truth for one entity, with provenance. |
| `GET` | `/health` and `/ready` | Both | Liveness and readiness, distinguished, per service. |

### Requirements

1. **Loading and provenance.** Every supplied record lands in PostgreSQL with the file and line it
   came from. `load_seed` is idempotent and re-running does not duplicate. Report what you
   accepted, what you coerced and what you rejected, and why.
2. **Reconciliation identity.** `records_read = records_in_ledger + records_quarantined +
   records_rejected`, per source file and in total. Asserted in a test and printed by the command.
   No record disappears without appearing in a count.
3. **Projection integrity.** Neo4j is rebuildable from PostgreSQL and nothing else writes to it.
   `reconcile_projection` must detect a graph that has drifted from the ledger, and you must prove
   it detects one by making it fail on purpose in a test.
4. **Audit.** Every request to `/api/v1/ask` writes one immutable audit record to PostgreSQL before
   a response is returned, including the ones the service refuses. The record holds at minimum the
   question as received, the generated Cypher, whether it was executed, the model name and digest,
   the schema registry version, the citations returned, and the outcome class. `replay_audit` must
   be able to reconstruct what happened from that record alone.
5. **Guarded query generation.** `/api/v1/ask` generates Cypher using the local model. The
   queryable surface is constrained by `reference/graph_schema_registry.json`. The registry is the
   authority, not the database. Generated queries that fall outside it do not execute.
6. **Read only.** No generated query may write. Demonstrate this at more than one layer, and state
   which layer you would trust if the others failed. The Neo4j credential used by the query path
   is part of your answer.
7. **Bounded execution.** Every query is bounded in time, in result size and in traversal depth. A
   question that cannot be answered within those bounds returns a bounded-out response, not a
   timeout and not a hang.
8. **Grounding.** Every answer cites the specific nodes and relationships it rests on, by
   identifier. An answer with no citations is not an answer.
9. **Abstention.** The service never presents information it cannot verify against the graph. Every
   question submitted to `/api/v1/ask` receives an answer grounded in cited graph nodes.
10. **Effective dating.** Several relationship types carry validity intervals. Every query and every
   endpoint that returns a fact about a point in time accepts an as-of date and defaults
   explicitly.
11. **Conflicts.** Where the graph asserts two incompatible facts, the response reports both, with
   their sources and dates. Silent selection of one is a failure.
12. **Determinism.** Identical request plus identical pinned artifacts produce an identical response
   body.
13. **Vector store.** Used for entity and question grounding. Justify what you put in it and what
    you deliberately did not, and say which store it is rebuildable from.
14. **Scope.** The service describes structure. It does not score, rate, rank, price or recommend a
    credit decision about any entity.

---

## 5. Evaluation harness

`data/eval/eval_questions.jsonl` contains 48 questions and no answers. You will build the harness
that runs them and produces `EVAL_REPORT.md` automatically from a command.

1. Derive your own taxonomy for the questions. Classify all 48. Your taxonomy and your reasoning
   are part of what is assessed.
2. Report per-class metrics. Choose them and justify them. At minimum you must be able to answer:
   how often does the service assert something the graph does not support, and how do you know?
3. Establish and report your own ground truth for every question you claim to answer correctly, and
   show how you established it.
4. Report the questions your service handled badly. A report with no failures in it will be read as
   a report that was not run.
5. The harness runs offline against the compose stack and is reproducible from a single command.

---

## 6. Security requirements

You will produce `SECURITY_NOTE.md`, no more than 600 words.

1. State your trust boundaries explicitly. Which inputs does the service treat as trusted, and why?
2. Content retrieved from the graph is untrusted, including content the service retrieved itself.
   Show where that assumption is enforced in code, and test it.
3. Validate payload integrity on every endpoint. Size, shape, unknown fields, encoding, and
   anything else you consider load-bearing. Say what you reject and what you normalise.
4. State what an authenticated caller can reach that an unauthenticated one cannot, and what you
   would add before this service saw a real counterparty's data.
5. State what in your Django configuration would have to change before this ran anywhere other
   than your laptop, and why it is as it is today.
6. Name three attacks your design defeats and **one it does not**. The last one is not optional and
   we will ask about it.

Generic middleware copied from a model's suggestion, with no threat specific to this service named,
scores zero on this section.

---

## 7. Judgement requirements

Graded as heavily as the code.

1. **A requirement you should refuse.** Product wants `/api/v1/ask` to return, alongside every
   answer, a 0 to 100 counterparty risk score derived from the graph, with a recommended credit
   limit, to be shown to a lending officer. Implement it or refuse it, in writing, with reasoning.
   Both answers can score full marks. Only an unexamined one scores zero.
2. **A negative result.** Report one thing you tried that made the service worse, and what you did
   about it.
3. **Anything in this brief that is wrong.** If a requirement cannot be satisfied as written, or two
   requirements conflict, say so, say what you did instead, and say what you would need from us to
   resolve it. There is at least one such requirement in this document.

---

## 8. Tests

At least 18 meaningful automated tests, all passing offline. Minimum coverage:

| Area | Expectation |
| --- | --- |
| Reconciliation | The record identity in requirement 2 holds for every source file. |
| Load idempotency | Re-running `load_seed` and `project_graph` does not duplicate ledger rows, nodes or relationships. |
| Projection drift | `reconcile_projection` fails when the graph is deliberately made to disagree with the ledger. |
| Audit completeness | An audit record exists for a successful query, an abstention and a refusal, and `replay_audit` reconstructs each. |
| Schema conformance | The surface exposed by `/api/v1/schema` matches the registry, and nothing else is reachable. |
| Write refusal | A generated or supplied query containing a write clause never executes. |
| Bounds | Depth, time and result-size limits hold under a pathological traversal. |
| Effective dating | The same question at two as-of dates returns different, correct answers. |
| Conflicts | An entity with contradictory assertions returns both, with sources. |
| Abstention | A question outside the schema does not receive a fabricated answer. |
| Untrusted content | Text stored in graph properties cannot alter query generation or response behaviour. |
| Payload integrity | Oversized, malformed and unknown-field payloads are rejected before reaching the model. |
| Determinism | Identical request and artifacts, identical response body. |
| Degradation | The service behaves correctly and states so when the local model is unavailable. |

---

## 9. Deliverables

- Source, `docker-compose.yml`, Django migrations, Neo4j constraints, loader and projection
  commands, and reproducible commands throughout
- `EVAL_REPORT.md`, generated by your harness, plus the command that generates it
- Your question taxonomy and classification of all 48 questions
- `README.md`, `AI_USE.md`, `DECISIONS.md`, `SECURITY_NOTE.md`
- Example request and response for a successful query, an abstention, a conflict and a rejection
- The `verify_pack.py` output
- Recorded actual hours, and a list of what you did not finish

`README.md` must be sufficient for someone to clone and run the whole thing without asking you
anything. Include the exact `ollama pull` command and the model digest.

---

## 10. Scoring

| Dimension | Points |
| --- | --- |
| Service correctness, containerisation and cold-start reproducibility | 15 |
| Query generation guarding and schema constraint injection | 20 |
| Ledger, projection integrity, reconciliation and audit | 15 |
| Graph modelling, effective dating and conflict handling | 10 |
| Evaluation harness and honesty of the report | 15 |
| Testing and failure handling | 10 |
| Security reasoning | 5 |
| Judgement, candour and scope control | 10 |

---

## 11. Oral defence

Forty minutes. Demo, walk-through, and a live change to your own code implemented in twenty minutes
**with no AI assistance**, plus one new test. The change will be a new relationship type or a new
constraint on query generation that you have not seen. Build accordingly.

## 12. Automatic fail

- The stack does not come up from a cold `docker compose up` following the README.
- Any runtime call to a hosted model API.
- Tests require network access or undisclosed credentials.
- A generated query executes a write.
- Neo4j is treated as the system of record, or is written to by anything other than the projection
  command.
- A request is answered or refused without an audit record.
- The service returns a credit decision, score, rating or limit.
- An answer is returned with no citation to graph nodes.
- Material LLM use is concealed.
- The candidate cannot explain or safely modify their own core code.
