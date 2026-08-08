# SECURITY_NOTE.md

## Trust boundaries

The submitted runtime services are local and Docker-based; no hosted LLM runtime API is required. Checked-in application code and infrastructure configuration define the current scaffold. `.env` is ignored, while `.env.example` contains development placeholders.

The supplied schema registry is the planned authority for the future queryable surface. Supplied data, graph properties, user questions, model output, and generated Cypher are untrusted. The submitted application does not implement business ingestion, indexing, projection, or querying, so those future boundaries are documented but not enforced in a business path.

## Untrusted content handling

Text from supplied data or a future graph must be treated only as untrusted data and must never become model instructions. Generated Cypher would also be untrusted future input and would require deterministic schema, write, depth, result-size, and time checks before execution.

Those controls and their tests are not implemented. Current application behavior is limited to health and readiness scaffolding, which does not accept business content.

## Payload and output integrity

The implemented health and readiness endpoints accept no business payload and report service or dependency status. Weaviate built-in vectorization and modules are disabled with `DEFAULT_VECTORIZER_MODULE: none` and `ENABLE_MODULES: ""`.

There is currently no authentication or authorization layer, so authenticated and unauthenticated callers have no different permissions. The only implemented HTTP surfaces are health and readiness endpoints. Before handling real counterparty data, I would add authenticated access, role-based authorization, restricted ledger and audit access, private service networking, TLS, rate limiting, and separate least-privilege service credentials.

Business payload validation, unknown-field rejection, prompt-injection defenses, Text2Cypher validation, Cypher guards, query bounds, separate read-only Neo4j query credentials, citation enforcement, and audit persistence are not implemented.

Before Django ran anywhere other than a developer laptop, I would set `DEBUG=False`, use an externally managed `SECRET_KEY`, restrict `ALLOWED_HOSTS`, use production PostgreSQL credentials, configure HTTPS-aware proxy settings, secure session and CSRF cookies, define trusted CSRF origins, enable production logging, and restrict access to ledger and audit endpoints. The current settings are development-only because this submission is limited to local scaffold verification.

## Three attacks this design defeats

1. **Data exfiltration to a hosted LLM provider through an inference API.** The runtime uses only the local Ollama service defined in Docker Compose and makes no hosted LLM API calls.
2. **Accidental secret disclosure through an ordinary commit.** `.gitignore` excludes `.env`, while the tracked `.env.example` contains only placeholder development values.
3. **Unintended use of a default or untrusted embedding model.** Weaviate built-in vectorization is disabled with `DEFAULT_VECTORIZER_MODULE: none` and `ENABLE_MODULES: ""`.

## One attack this design does not defeat

A hostile caller to future business or query endpoints is not currently controlled. Authentication, authorization, payload validation, prompt-injection handling, deterministic Cypher guards, bounded graph execution, citation enforcement, and audit persistence would all be required before exposing those endpoints.
