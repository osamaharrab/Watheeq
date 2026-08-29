# Security note

## Trust boundaries

Trusted inputs are the supplied schema/registry configuration and PostgreSQL source records after ingestion validation. PostgreSQL is authoritative. Neo4j is a derived, rebuildable projection, and Weaviate is a grounding index rather than business truth.

Untrusted inputs include user questions, client headers and request bodies, model-generated Cypher, and text retrieved from Weaviate or Neo4j. Retrieved graph text is data, not an instruction for the model or query path.

## Implemented controls

- Credentials are supplied through environment variables. `GRAPH_DB_PASSWORD` has no Python fallback.
- FastAPI request models validate shape and reject unknown fields. A middleware enforces an 8,192-byte request-body limit, including when `Content-Length` is missing or false.
- Generated Cypher is treated as untrusted. The deterministic guard allows only the registered node labels, `HOLDS_INTEREST_IN`, registered properties, known aliases, and the approved parameters.
- The guard requires a read-only `MATCH`/`RETURN` query with deterministic ordering, one literal limit, bounded traversal, and the required current or inclusive historical date rules. Write, destructive, schema-bypass, and unsupported requests are refused before execution.
- Neo4j query sessions use read access. Queries are parameterized, have a three-second timeout, a maximum depth of four, and a maximum of 100 returned rows.
- The local model plans Cypher once and does not write final business answers. Citations and deterministic responses are built from verified graph facts. Each `/api/v1/ask` outcome is written to the immutable PostgreSQL audit trail; audit failure fails the request closed.
- `/health` checks process liveness. `/ready` additionally checks Django, Neo4j, Weaviate, and the required Ollama model and digest.

## Three attacks or abuses defeated

1. **Graph write attempt:** A question asking to create, delete, or alter graph data is refused. Generated Cypher with write clauses also fails the deterministic guard and does not run.
2. **Schema-bypass or property-enumeration attempt:** The guard rejects unknown labels, relationships, aliases, properties, and parameters, so generated Cypher cannot inspect arbitrary graph fields.
3. **Oversized request:** Requests over 8,192 bytes receive HTTP 413 even if the caller omits or lies about `Content-Length`.

## A control not fully implemented

The current local assessment setup has no authenticated caller role, so authenticated and unauthenticated callers do not have different application-level access.

There is no caller authentication or service-to-service authentication in this local assessment setup. In particular, the Django internal audit endpoint accepts valid-shaped requests without a dedicated service credential. A party able to reach that endpoint could create new audit records, although existing immutable records cannot be changed through the application.

Before handling real counterparty data, I would add caller authentication and authorization, service-to-service authentication for audit writes, network restrictions for internal endpoints, TLS, protected secret management, `DEBUG=0`, a strong external Django secret key, restricted allowed hosts, and non-development database credentials.
