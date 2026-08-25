# AI_USE.md

## Tools and models used

Codex was used as an implementation assistant for the project scaffold, Docker Compose and configuration wiring, health and readiness endpoints, verification commands, and documentation edits. During post-submission continuation, Codex also substantially assisted with the Django registry models, ingestion logic, ownership normalization, `load_seed` command, the simple ownership graph projection and reconciliation, `project_graph` and `reconcile_projection` commands, Neo4j constraints, Django Neo4j driver dependency update, the schema registry loader and endpoint, schema-version persistence, focused tests, and readability guidance.

ChatGPT assisted with assessment interpretation, scope review, architecture discussion, implementation-decision review, review of code and verification output, and preparation of implementation instructions. The exact ChatGPT and Codex model identifiers were not recorded. Neither ChatGPT nor Codex independently chose the final architecture or scope. Ollama `qwen3:4b` is configured as the local runtime model, but the application does not yet prompt it.

## Components that received substantial assistance

AI assistance was substantial in the Django and FastAPI scaffolds, service and environment wiring, Docker Compose dependency configuration, health and readiness checks, documentation structure, and review of verification results.

In the post-submission continuation, assistance was also substantial in implementing and explaining `IngestionRecord`, `LegalEntity`, `NaturalPerson`, `Filing`, `OwnershipInterest`, `SchemaRegistryState`, provenance-preserving ingestion, ownership normalization, the real `load_seed` command, the rebuildable Neo4j ownership projection, the real `project_graph` command, the two ownership-slice uniqueness constraints, the Neo4j dependency update, the simple read-only reconciliation implementation, the real `reconcile_projection` command, the authoritative registry loader, the ownership-only schema endpoint, 24 Django tests, and 8 focused FastAPI tests.

Grounding, embeddings, Text2Cypher, query guards, audit, and question answering remain unimplemented.

## Suggestions rejected or materially corrected

1. Application-facing connection variables initially used the `NEO4J_*` namespace. I corrected them to `GRAPH_DB_URI`, `GRAPH_DB_USER`, and `GRAPH_DB_PASSWORD` because Neo4j can interpret `NEO4J_*` variables as server configuration, making the setup less reliable. Successful service startup and connectivity during the recorded implementation work verified the corrected configuration.
2. An early Weaviate configuration could have implied that its default setting alone was sufficient. I explicitly disabled built-in vectorization and modules with `DEFAULT_VECTORIZER_MODULE: none` and `ENABLE_MODULES: ""` because the intended future design uses externally generated local embeddings. The retained Compose configuration and successful Weaviate readiness check during the recorded implementation work verified that configuration.
3. I rejected the assumption that `OLLAMA_MODEL=qwen3:4b` installs the model. Ollama requires a separate `ollama pull qwen3:4b`; the local model list and tags response were checked during the recorded implementation work.
4. I rejected descriptions of planning stubs as implemented functionality. In the original submission they were explicitly marked `PLANNED ONLY`. During later implementation, the temporary `planned_commands/` directory was removed, the real `load_seed` command moved to Django's management-command path, and future assessment modules remained clearly identified as planned.

## Verification performed

The assessment pack was checked with the supplied verification script. During the original recorded implementation work, the Compose configuration, service startup order, Django system checks, PostgreSQL and Neo4j connectivity, Weaviate readiness, Ollama model availability and digest, and Django/FastAPI health and readiness endpoints were checked.

For the post-submission Django data foundation, the developer manually reviewed the generated code, generated and inspected `registry/migrations/0001_initial.py`, applied the migration, ran the Django system check, ran all 16 Django tests, ran seed ingestion twice, inspected the resulting accounting, and checked the actual PostgreSQL row counts before accepting the implementation.

For the ownership graph projection, the developer manually reviewed the implementation, ran the Django system check, passed the 3 focused graph-projection tests and all 19 Django tests, ran `project_graph` twice with identical counts, and visually inspected the resulting graph in Neo4j.

For projection reconciliation, the developer manually reviewed the implementation, ran the 3 focused reconciliation tests, ran reconciliation against the real PostgreSQL and Neo4j services, introduced deliberate same-count ownership drift, confirmed that the command detected the mismatch, rebuilt Neo4j with `project_graph`, and confirmed that reconciliation succeeded afterward.

For the schema registry foundation, the implementation was compiled and reviewed, both changed service images were built, the migration and Django system check were run, all 24 Django tests passed with the documented read-only seed-data mount, all 8 FastAPI tests passed, the PostgreSQL version value was read directly, and the running health, readiness, and schema endpoints were checked. The first full Django test invocation without the existing seed-data mount failed clearly and was not treated as a passing result.

This documentation-only accuracy pass did not rerun Docker, services, tests, migrations, seed ingestion, or network checks.

## Where you relied on your own judgement instead of generated output

I retained responsibility for the final architecture and scope, keeping PostgreSQL and Django authoritative, treating Neo4j as a rebuildable projection, selecting ownership as the first business vertical slice, choosing local Ollama, refusing automated risk scores and credit-limit recommendations, deciding what remained intentionally unfinished, reviewing generated code, and accepting changes only after the manual checks described above.

## Unresolved concerns

The main remaining assessment gaps are grounding and embeddings, guarded and bounded Text2Cypher, citations, audit persistence and replay, authentication and authorization, the evaluation harness, and complete assessment-wide test coverage. The current 24 Django tests and 8 FastAPI tests cover the implemented Django data foundation, ownership graph projection, projection reconciliation, schema state, authoritative registry loading, and ownership-only schema endpoint.
