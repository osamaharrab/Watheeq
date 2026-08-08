# AI_USE.md

## Tools and models used

Codex was used as an implementation assistant for the project scaffold, Docker Compose and configuration wiring, health and readiness endpoints, verification commands, and documentation edits.

The exact Codex model identifier was not recorded. Codex did not independently choose the final architecture or submission scope. Ollama `qwen3:4b` was configured as the local runtime model, but the submitted application does not prompt it.

## Components that received substantial assistance

AI assistance was substantial in the Django and FastAPI scaffolds, service and environment wiring, Docker Compose dependency configuration, health and readiness checks, documentation structure, and review of verification results.

Business ingestion, graph projection, grounding, Text2Cypher, audit, and question answering remain unimplemented.

## Suggestions rejected or materially corrected

1. Application-facing connection variables initially used the `NEO4J_*` namespace. I corrected them to `GRAPH_DB_URI`, `GRAPH_DB_USER`, and `GRAPH_DB_PASSWORD` because Neo4j can interpret `NEO4J_*` variables as server configuration, making the setup less reliable. Successful service startup and connectivity during the recorded implementation work verified the corrected configuration.
2. An early Weaviate configuration could have implied that its default setting alone was sufficient. I explicitly disabled built-in vectorization and modules with `DEFAULT_VECTORIZER_MODULE: none` and `ENABLE_MODULES: ""` because the intended future design uses externally generated local embeddings. The retained Compose configuration and successful Weaviate readiness check during the recorded implementation work verified that configuration.
3. I rejected the assumption that `OLLAMA_MODEL=qwen3:4b` installs the model. Ollama requires a separate `ollama pull qwen3:4b`; the local model list and tags response were checked during the recorded implementation work.
4. I rejected descriptions of planning stubs as implemented functionality. The retained planning stubs are explicitly marked `PLANNED ONLY` and contain no business implementation; static review confirmed they contain documentation only.

## Verification performed

The assessment pack was checked with the supplied verification script. During the recorded implementation work, the Compose configuration, service startup order, Django system checks, PostgreSQL and Neo4j connectivity, Weaviate readiness, Ollama model availability and digest, and Django/FastAPI health and readiness endpoints were checked.

This documentation-only correction pass did not rerun Docker, services, tests, or network checks.

## Where you relied on your own judgement instead of generated output

I retained responsibility for limiting the submission scope, keeping PostgreSQL and Django authoritative, treating Neo4j as a rebuildable projection, selecting ownership as the first planned business vertical slice, choosing local Ollama, refusing automated risk scores and credit-limit recommendations, deciding what remained intentionally unfinished, and reviewing verification results before accepting generated changes.

## Unresolved concerns

The main assessment functionality remains incomplete: business ingestion and provenance, graph projection and reconciliation, grounding, guarded and bounded Text2Cypher, citations, audit persistence, authentication and authorization, evaluation, and the required complete automated test suite are not implemented.
