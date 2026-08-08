# DECISIONS.md

## Decision 1: Submit a limited verified scaffold

**What I chose.**

I limited the implementation to the six-service Docker Compose scaffold, configuration and dependency wiring, and Django/FastAPI health and readiness endpoints. Ownership questions are the planned first business vertical slice, but that slice is not implemented.

**What I rejected, and why.**

I rejected broad, incomplete business paths that could appear functional without end-to-end verification. Ownership is the load-bearing question in the brief and provides a bounded first path through ledger, projection, grounding, querying, citation, and audit.

**What would have to be true for the rejected option to be the better one.**

There would need to be enough time to implement and test ingestion, provenance, projection, reconciliation, guarded querying, citations, audit, and evaluation together.

**What this decision costs.**

Most assessed business functionality and the required complete test suite remain unfinished.

## Decision 2: Keep Django and PostgreSQL authoritative

**What I chose.**

PostgreSQL is the planned system of record, owned through Django. Neo4j is a rebuildable derived projection, and FastAPI does not own authoritative business writes.

**What I rejected, and why.**

I rejected treating Neo4j or Weaviate as authoritative because that would conflict with the brief and weaken provenance and reconciliation boundaries.

**What would have to be true for the rejected option to be the better one.**

The system would need a different, explicitly graph-native authority model with equivalent provenance, audit, recovery, and reconciliation guarantees.

**What this decision costs.**

The ledger, projection commands, and reconciliation checks must all be implemented before business graph results can be trusted.

## Decision 3: Plan external local embeddings for Weaviate

**What I chose.**

I configured Weaviate with internal vectorization disabled. The future grounding design would use local `all-MiniLM-L6-v2` embeddings with 384 dimensions, the same model for stored and query vectors, BM25 separately, and hybrid retrieval with a planned default alpha of `0.5`.

**What I rejected, and why.**

I rejected hosted embeddings and Weaviate-managed vectorization because runtime inference must remain local and explicit embedding generation gives the application control over model consistency.

**What would have to be true for the rejected option to be the better one.**

The runtime rules and data-governance boundary would need to permit a hosted or internally managed embedding service with reproducible model pinning.

**What this decision costs.**

Future implementation must add local model dependencies, embedding generation, indexing, rebuild behavior, and retrieval tests. None of that is implemented now.

## Decision 4: Run Ollama qwen3:4b inside Docker Compose

**What I chose.**

I configured Ollama inside Compose with `qwen3:4b`, using host port `11435` and container port `11434`. A fresh volume requires `ollama pull qwen3:4b`.

**What I rejected, and why.**

I rejected hosted inference because the brief prohibits it, and I rejected relying on a host Ollama process because it adds machine-specific networking and setup outside the stack.

**What would have to be true for the rejected option to be the better one.**

A host process would need to be a guaranteed reviewer prerequisite with stable networking, model storage, and version control. Hosted inference would require a change to the assessment rules.

**What this decision costs.**

The local model requires a separate pull, disk space, startup time, and enough CPU and memory on the reviewer machine.

## Decision 5: Refuse automated risk scoring and credit limits

**What I chose.**

I refused to implement a 0–100 counterparty risk score or recommended credit limit. A future service should return cited ownership and control facts for human review.

**What I rejected, and why.**

I rejected turning incomplete, conflicting, effective-dated synthetic graph records into a lending recommendation without an approved policy, validated outcomes, fairness review, explainability, and legal basis.

**What would have to be true for the rejected option to be the better one.**

It would require a separately governed decision system with validated data, approved policy, human oversight, monitoring, appeals, and legal and fairness review.

**What this decision costs.**

The service cannot provide the requested automated lending recommendation; it remains limited to factual structure if that future path is implemented.

## Decision 6: Correct the Neo4j application environment namespace

**What I chose.**

Application configuration initially used `NEO4J_*` connection variables. That namespace risked being interpreted as Neo4j server configuration and made the setup less reliable. I changed the application-facing variables to `GRAPH_DB_URI`, `GRAPH_DB_USER`, and `GRAPH_DB_PASSWORD`, then successfully verified service startup and connectivity.

**What I rejected, and why.**

I rejected keeping the original names as a cosmetic convention because their interaction with Neo4j server configuration was the problem that made the earlier setup worse.

**What would have to be true for the rejected option to be the better one.**

The `NEO4J_*` namespace would need to be unambiguous and isolated from Neo4j server environment processing.

**What this decision costs.**

The application uses a project-specific namespace that must be documented and kept consistent across Compose and FastAPI configuration.

## Decision 7: Define explicit answer, abstention, and refusal outcomes

**What I chose.**

I interpret Requirement 9 as requiring every `/api/v1/ask` request to receive an explicit outcome: a factual answer grounded in cited graph nodes, an abstention when the graph or schema cannot support a factual answer, or a refusal when the request is unsafe or outside the allowed scope. This is guidance for future implementation, not current behavior.

**What I rejected, and why.**

I rejected the literal reading that every question must receive a factual, cited answer. Requirement 9 also prohibits unverifiable information, while other parts of the brief explicitly require abstentions and refusals.

**What would have to be true for the rejected option to be the better one.**

The brief would need to state that all allowed questions are guaranteed to be answerable from the graph and clarify how unsafe requests fit the endpoint contract.

**What this decision costs.**

The future response and audit schemas must distinguish all three outcomes and test them separately.
