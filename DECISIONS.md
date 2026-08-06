# DECISIONS.md

## Decision 1: Limit the submission to a verified scaffold

I chose to submit a small scaffold that starts the required services and verifies basic connectivity. This includes Docker Compose, service wiring, health checks, readiness checks, and placeholder modules.

The trade-off is clear: the project does not yet ingest data, project a graph, answer questions, write audit records, or produce evaluation results. I preferred that over presenting unfinished business logic as complete.

## Decision 2: Keep PostgreSQL and Django as the planned source of truth

PostgreSQL is the planned system of record. Django is planned to own PostgreSQL writes, ingestion provenance, schema registry state, projection commands, and audit persistence.

I did not put business writes in FastAPI or Neo4j because that would blur the source-of-truth boundary required by the assessment. The cost is that useful business behavior still needs Django models, migrations, commands, and internal APIs.

## Decision 3: Treat Neo4j as a rebuildable projection

Neo4j is planned as a derived graph projection, rebuilt from PostgreSQL by the Django `project_graph` command.

This keeps PostgreSQL authoritative and makes projection drift something the system can detect later. The cost is that projection and reconciliation still have to be implemented before Neo4j query results can be trusted.

## Decision 4: Use FastAPI as the planned query orchestrator

FastAPI is planned to handle the query-facing path: grounding, local model use, Cypher validation, read-only graph access, deterministic answer construction, and audit submission back to Django.

I kept this responsibility out of Django because the assessment explicitly assigns the query path to FastAPI. The cost is an extra service boundary that must be kept simple and well tested.

## Decision 5: Use Weaviate for vector storage and search only

Weaviate is deployed and configured as the planned vector-storage and vector-search service:

```yaml
DEFAULT_VECTORIZER_MODULE: none
ENABLE_MODULES: ""
```

No vectors, embeddings, indexing, retrieval, or grounding are implemented yet. I disabled built-in vectorizers so future embeddings must be generated explicitly by local Python code. The cost is that the project still needs embedding and indexing work before Weaviate is useful.

## Decision 6: Run local Ollama with `qwen3:4b` inside Docker Compose

Ollama runs inside Docker Compose. FastAPI reaches it through `http://ollama:11434`. The host exposes Ollama on port `11435` because host port `11434` was unavailable.

I considered relying on a host-installed Ollama service, but that would add a separate machine dependency and cross-platform networking differences. Running Ollama in Compose gives reviewers one stack to start.

The trade-off is storage and hardware configuration. The model must still be pulled once into the Docker named volume on a new machine, and the installed model is about 2.5 GB. Runtime requests use `qwen3:4b`, not the digest. The verified digest is:

```text
359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7
```

## Decision 7: Treat future LLM output and generated Cypher as untrusted

The planned LLM role is narrow: generate candidate Cypher under schema constraints. Generated Cypher must be treated as untrusted code and pass deterministic validation before execution.

I rejected direct execution of model output because a generated write, unsupported schema access, or uncited claim would be unsafe and could trigger assessment failures. The cost is more implementation work around guards, bounds, read-only credentials, and citation checks.

## Decision 8: Exclude frontend and monitoring services

I did not add a frontend or monitoring stack. The assessment risk is in the data path, graph projection, guarded querying, audit, and evaluation, not in UI or observability tooling.

The cost is that there is no dashboard, metrics stack, tracing, or log aggregation.

## Decision 9: Keep supplied data immutable

The supplied data, reference files, templates, and assessment files are treated as immutable inputs.

I rejected cleaning or rewriting fixture data because the assessment expects the application to handle dirty, conflicting, temporal, and hostile records while preserving provenance. The cost is that future ingestion code must do the hard work instead of changing the source files.

## Decision 10: Use Docker Compose for local reproducibility

Docker Compose is used to start PostgreSQL, Django, Neo4j, Weaviate, FastAPI, and Ollama together.

I rejected Kubernetes, cloud deployment, and manually started services because they add scope without helping this take-home run locally. The cost is that the setup is local-development oriented and not production hardened.

## Decision 11: Refuse automated counterparty risk scoring

The planned service should expose traceable ownership and control facts. It should not produce a 0-100 counterparty risk score, a credit recommendation, or a recommended credit limit.

The assessment explicitly asks for a position on this kind of requirement. I would refuse it in this project because the supplied data is incomplete, conflicting, effective-dated, and may contain hostile content. Turning those records into a lending decision would be unsupported and high impact.

The safer output is cited facts, conflicts, provenance, and effective dates for authorised human review. Any scoring system would need a separately approved policy, validated labels, fairness analysis, explainability, human oversight, monitoring, appeal mechanisms, and legal review.

## Negative Result

The application-facing Neo4j connection variables initially used the `NEO4J_*` prefix. Neo4j treats that namespace as server configuration, so those names were a bad fit for application connection settings.

I changed them to `GRAPH_DB_URI`, `GRAPH_DB_USER`, and `GRAPH_DB_PASSWORD`. The correction was verified with Docker Compose startup, healthy service status, and a successful `RETURN 1 AS ok` query.

## Requirement Interpretation: Answers, Abstentions, and Refusals

I interpret the future `/api/v1/ask` outcomes as:

- A factual answer supported by graph node and relationship citations.
- An abstention because the graph does not support an answer.
- A refusal because the request is unsafe or outside scope.

Only factual claims require graph-node and relationship citations. Abstentions and refusals still need an explicit outcome type and reason. Every outcome is planned to be written to the audit ledger.

This interpretation is documented only. It is not implemented.
