# SECURITY_NOTE.md

## Trust boundaries

The submitted runtime services are local and Docker-based; no hosted LLM runtime API is required. Checked-in application code and infrastructure configuration define the current scaffold. `.env` is ignored, while `.env.example` contains development placeholders.

The supplied schema registry is the planned authority for the future queryable surface. Supplied JSONL data, graph properties, user questions, model output, and generated Cypher are untrusted. Seed ingestion is now implemented in Django; indexing, graph projection, and querying remain unimplemented.

## Untrusted content handling

Seed ingestion decodes and parses each physical JSONL line, preserves its raw payload and source provenance, and normalizes only the supported registry fields. Unsupported fields remain in the raw ledger instead of expanding the authoritative model. Hostile or prompt-like text remains inert business data. The only non-ISO coercion is the narrow fixture-backed `DD/MM/YYYY` conversion for `LE-023`; other unsafe or unresolved records are rejected or quarantined with reasons.

Text later retrieved from a graph must still be treated as untrusted data and never as model instructions. Model prompting, Text2Cypher, deterministic schema and write guards, depth/result/time bounds, read-only query credential separation, citations, and query audit persistence are not implemented.

## Payload and output integrity

The implemented health and readiness endpoints accept no business payload and report service or dependency status. Seed ingestion is a local Django management-command path, not a public HTTP endpoint. Weaviate built-in vectorization and modules are disabled with `DEFAULT_VECTORIZER_MODULE: none` and `ENABLE_MODULES: ""`.

There is currently no authentication or authorization layer, so authenticated and unauthenticated callers have no different permissions. The only implemented HTTP surfaces are health and readiness endpoints. Before handling real counterparty data, I would add authenticated access, role-based authorization, restricted ledger and audit access, private service networking, TLS, rate limiting, and separate least-privilege service credentials.

FastAPI business payload validation, authentication, authorization, graph projection, model prompting, Text2Cypher validation, Cypher guards, query bounds, separate read-only Neo4j query credentials, citation enforcement, and query audit persistence are not implemented.

Before Django ran anywhere other than a developer laptop, I would set `DEBUG=False`, use an externally managed `SECRET_KEY`, restrict `ALLOWED_HOSTS`, use production PostgreSQL credentials, configure HTTPS-aware proxy settings, secure session and CSRF cookies, define trusted CSRF origins, enable production logging, and restrict access to ledger and audit endpoints. The current settings remain development-only.

## Three attacks this design defeats
At the current implementation stage, these are configuration-level protections against specific failure modes, not complete adversarial security guarantees.
1. **Data exfiltration to a hosted LLM provider through an inference API.** The runtime uses only the local Ollama service defined in Docker Compose and makes no hosted LLM API calls.
2. **Accidental secret disclosure through an ordinary commit.** `.gitignore` excludes `.env`, while the tracked `.env.example` contains only placeholder development values.
3. **Unintended use of a default or untrusted embedding model.** Weaviate built-in vectorization is disabled with `DEFAULT_VECTORIZER_MODULE: none` and `ENABLE_MODULES: ""`.

## One attack this design does not defeat

A hostile caller to future business or query endpoints is not currently controlled. Authentication, authorization, payload validation, prompt-injection handling, deterministic Cypher guards, bounded graph execution, citation enforcement, and audit persistence would all be required before exposing those endpoints.
