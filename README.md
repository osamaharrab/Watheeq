# Watheeq Take-Home Assessment

## What I Implemented

Runtime implementation has not started yet.

Completed work:

- Read and analysed the assessment requirements.
- Reviewed the supplied graph data and schema registry.
- Understood the intended service boundaries and main data flow.
- Defined a deliberately limited implementation plan.
- Verified the supplied assessment pack successfully using `scripts/verify_pack.py`.
- Generated and committed `PACK_VERIFICATION.json`.

## What I Did Not Implement

The application services and runtime path have not been implemented yet.

Work not started yet:

- Django and PostgreSQL system-of-record layer.
- Neo4j graph projection.
- FastAPI query service.
- Vector grounding.
- Local Ollama integration.
- Docker Compose runtime.
- Tests and evaluation.
- Final documentation.

Deliberately excluded from the planned limited scope:

- Complete support for all 48 evaluation questions.
- Advanced beneficial-ownership calculations.
- Broad multi-hop graph reasoning.
- Complete query support for assets, instruments, pledges, and filings.
- Advanced conflict resolution beyond explicitly supported cases.

This README is being written before implementation begins and will be updated with the final status.

## Why I Chose This Scope

The assessment is intentionally broader than the available time. I am choosing a small, correct, tested, and fully understood end-to-end path instead of attempting broad feature coverage that I cannot verify.

The implementation will prioritise correctness, provenance, clear service boundaries, read-only graph access, citations, auditability, safe abstention, and code that can be explained and modified during the oral defence.

### Scope Decisions

Direct ownership queries are the initial supported path because they exercise the complete architecture: ingestion into PostgreSQL, provenance preservation, projection into Neo4j, read-only querying, optional effective-date filtering, graph citations, and audit recording.

Advanced beneficial ownership and broad multi-hop reasoning are deliberately outside the initial scope because correct implementation requires cycle handling, multiple-path reasoning, conflict handling, and additional verification.

Complete support for all 48 evaluation questions is deliberately outside this planned limited scope. Unsupported question types will produce an explicit, audited abstention instead of an unverified answer.

## Planned Implementation

1. Load the supplied JSONL records through Django into PostgreSQL.
2. Preserve the original payload and provenance, including source file and source line.
3. Keep Django and PostgreSQL as the system of record.
4. Project the required graph data into Neo4j only through the Django `project_graph` command.
5. Use FastAPI as the query-facing service.
6. Initially support a narrow set of direct ownership queries, including an optional as-of date.
7. Return graph node and relationship citations with successful answers.
8. Record every `/api/v1/ask` answer, abstention, and refusal through Django.
9. Prevent write queries and use read-only Neo4j access for the FastAPI query path.
10. Use only a local Ollama model at runtime.
11. Return an explicit abstention for unsupported questions rather than inventing an answer.

## Architecture Overview

```text
JSONL data
    ↓
Django
    ↓
PostgreSQL — system of record
    ↓
Django project_graph
    ↓
Neo4j — derived projection

User request
    ↓
FastAPI
    ↓
Guarded read-only Neo4j query
    ↓
Answer with citations or abstention
    ↓
Django audit record
```

FastAPI will communicate with Django through internal HTTP APIs rather than writing directly to PostgreSQL.

## Time Log

| Date                     | Time        |       Hours | Work completed                                                            |
| ------------------------ | ----------- | ----------: | ------------------------------------------------------------------------- |
| Wednesday, 5 August 2026 | 07:00–10:00 |           3 | Reviewed the assessment, architecture, and project requirements           |
| Wednesday, 5 August 2026 | 17:00–19:00 |           2 | Reviewed the supplied data and schema and defined the implementation plan |
| **Total recorded time**  |             | **5 hours** | Understanding, data review, and planning                                  |



## Setup and Run

To be updated after implementation.

## Implemented Commands

To be updated after implementation.

## Implemented Endpoints

To be updated after implementation.

## Tests and Evaluation

To be updated after implementation.

## Known Limitations

To be updated after implementation.

## AI Use

To be updated after implementation.

## Final Time Summary

To be updated after implementation.
