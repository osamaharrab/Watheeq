# SECURITY_NOTE.md

## Current Security Position

This repository is a development scaffold, not a production-ready system.

The supplied assessment files are treated as immutable, but their content is still untrusted. Future ingestion and query code must assume the data may be dirty, conflicting, temporal, or hostile.

`.env` is ignored by Git. `.env.example` contains development placeholders only. Secrets should come from environment variables and should not be copied into documentation or command examples.

There is no authentication or authorization layer. Authenticated and unauthenticated callers have no different permissions. The only implemented HTTP functionality is `/health` and `/ready` on the Django and FastAPI services.

## Current Configuration Protections

No hosted LLM API is configured. Ollama runs locally inside Docker Compose, and FastAPI is configured to reach it internally at `http://ollama:11434`.

Weaviate built-in vectorizer modules are disabled:

```yaml
DEFAULT_VECTORIZER_MODULE: none
ENABLE_MODULES: ""
```

These are configuration protections against specific mistakes. They are not a complete security system.

## Missing Controls

The main missing controls are:

- Authentication and authorization.
- Payload validation.
- Unknown-field rejection.
- Request-size limits.
- Encoding validation.
- Prompt-injection protection.
- Deterministic Cypher validation.
- Write-query rejection.
- Query timeouts and result limits.
- Read-only Neo4j credentials for the query path.
- Citation enforcement.
- Audit persistence.
- Refusal and abstention recording.
- Rate limiting.
- TLS and private networking.

Generated Cypher must eventually be treated as untrusted code. It should not execute until deterministic guards prove that it is read-only, schema-constrained, and bounded.

## Django Before Production

Before Django runs outside a developer laptop, it would need `DEBUG=False`, an externally managed `SECRET_KEY`, restricted `ALLOWED_HOSTS`, secure PostgreSQL credentials, HTTPS-aware proxy settings, secure session cookies, secure CSRF cookies, explicit CSRF trusted origins, production logging, and restricted access to ledger and audit endpoints.

Those controls are not implemented in this scaffold.

## What This Does Not Defeat

The current scaffold does not defeat prompt injection, malicious generated Cypher, unauthorized access, payload abuse, missing citations, or unaudited refusals and abstentions.

Those risks remain because the ingestion path, query path, guards, audit persistence, authentication, authorization, and evaluation are not implemented.
