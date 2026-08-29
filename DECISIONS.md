# Engineering decisions

## 1. Narrow ownership vertical slice

**Decision:** Implement `LegalEntity`, `NaturalPerson`, and `HOLDS_INTEREST_IN` end to end.

**Why:** A complete slice was more useful than partial support for every supplied relation.

**Alternative not chosen:** Broad support for assets, instruments, pledges, and other relations without the same ingestion, projection, reconciliation, query, and test coverage.

## 2. PostgreSQL is authoritative

**Decision:** Keep normalized records, provenance, and audit records in PostgreSQL through Django.

**Why:** PostgreSQL is the record of truth for ingested data and audit persistence.

**Alternative not chosen:** Treating Neo4j as the authoritative database.

## 3. Neo4j is derived and rebuildable

**Decision:** Rebuild Neo4j from PostgreSQL and reconcile it against PostgreSQL.

**Why:** Neo4j supports ownership traversal without becoming an independent source of truth.

**Alternative not chosen:** Maintaining graph facts separately from the ledger.

## 4. Ownership stays in bps

**Decision:** Store and return ownership as integer `bps`.

**Why:** This is the supplied schema’s native unit. 10,000 bps equals 100 percent, and no percentage property is invented.

**Alternative not chosen:** Silent conversion to decimal or percentage fields.

## 5. Inclusive effective dating

**Decision:** Treat current ownership as `valid_to = null`; for historical queries use `valid_from <= as_of` and `(valid_to is null OR as_of <= valid_to)`.

**Why:** This preserves the supplied validity fields and makes the end date inclusive.

**Alternative not chosen:** Selecting only a latest record or treating `valid_to` as exclusive.

## 6. Weaviate is grounding, not truth

**Decision:** Use Weaviate for entity and question grounding only.

**Why:** It discovers candidates. Business relationships are verified from Neo4j’s projection of PostgreSQL data.

**Alternative not chosen:** Answering ownership questions from vector-search results.

## 7. Exact resolution before hybrid retrieval

**Decision:** Resolve exact IDs and names before using hybrid lexical/vector discovery.

**Why:** Exact identity should not be diluted by semantic candidates. When an exact legal name is non-unique, all exact matches are kept.

**Alternative not chosen:** Always using hybrid retrieval first.

## 8. Deterministic guard for generated Cypher

**Decision:** Treat model-generated Cypher as untrusted and validate it before execution.

**Why:** Only the allowed schema, read-only query shape, labels, relationship types, properties, parameters, bounds, and temporal rules may reach Neo4j.

**Alternative not chosen:** Relying only on model instructions to keep queries safe.

## 9. Explicit non-answer outcomes

**Decision:** Distinguish `answered`, `unsupported`, `abstained`, and `refused` outcomes.

**Why:** Answered responses require verified ownership facts. Requests outside the slice are unsupported; ownership requests that cannot be grounded or proved safely abstain; unsafe requests are refused. The local planner can still be over-conservative, so remaining classification failures are retained rather than hidden.

**Alternative not chosen:** Returning a plausible-looking answer for every question.

## 10. No risk or credit decisions

**Decision:** Do not implement counterparty risk scores, credit scores, lending limits, or recommendations.

**Why:** They are outside the supported graph facts and policy scope. The service provides cited ownership facts, not lending advice.

**Alternative not chosen:** Deriving a score from incomplete ownership data.

## 11. Ownership-only ask endpoint

**Decision:** Keep `/api/v1/ask` limited to the current `HOLDS_INTEREST_IN` slice. The local model plans ownership intent and guarded Cypher once; final answers are rendered deterministically from verified Neo4j relationship facts. A plan that drops an explicit named ownership endpoint fails closed before graph execution.

**Why:** This avoids general-chat answers, citation/value mismatches, and partial relationship answers while keeping the audit, guard, and graph-execution plumbing reusable for a later relationship slice.

## Negative result

Using hybrid retrieval directly for an exact company-name question returned several candidates and produced an incorrect ownership query. Runtime `/api/v1/entities/resolve` and `/api/v1/ask` results, together with focused grounding tests, showed the problem. Exact-first resolution replaced hybrid-first retrieval.

## Brief interpretation

The brief requires grounded answers with citations and also requires abstention, refusal, and unsupported behaviour. I interpreted this as requiring citations for answered business claims. Unsupported, abstained, and refused responses are explicit non-answer outcomes, so they must not fabricate citations merely to fit an answer format.

To resolve this interpretation formally, I would ask Watheeq to confirm whether unsupported, abstained, and refused outcomes are exempt from the citation requirement that applies to answered business claims.
