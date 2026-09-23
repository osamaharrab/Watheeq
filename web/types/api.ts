// TypeScript mirrors of the real backend contracts.
// FastAPI: fastapi_service/app/schemas.py
// Django:  django_service/registry/views.py and registry/audit.py
// Keep these in step with the backend; the backend is authoritative.

export type EntityType = "LegalEntity" | "NaturalPerson";

// ---------- FastAPI: POST /api/v1/entities/resolve ----------

export interface EntityMatch {
  type: EntityType;
  canonical_id: string;
  display_name: string;
  // LegalEntity: { jurisdiction, registration_no }; NaturalPerson: { nationality }.
  // Typed loosely because the backend declares it as dict[str, Any].
  metadata: Record<string, unknown>;
  match_method: "exact" | "hybrid";
}

export interface EntityResolveResponse {
  matches: EntityMatch[];
}

// ---------- FastAPI: GET /api/v1/entities/{entity_uid}/ownership ----------

export interface OwnershipFact {
  relationship: "HOLDS_INTEREST_IN";
  holder_type: EntityType;
  holder_uid: string;
  held_entity_uid: string;
  bps: number;
  valid_from: string;
  valid_to: string | null;
  filing_uid: string | null;
  citation_id: string;
}

export interface OwnershipPathNode {
  type: EntityType;
  canonical_id: string;
  display_name: string;
}

export interface OwnershipPath {
  // Ordered from the upstream holder down to the requested entity.
  nodes: OwnershipPathNode[];
  relationships: OwnershipFact[];
  cycle: boolean;
}

export interface OwnershipResponse {
  entity_uid: string;
  temporal_mode: "current" | "as_of";
  as_of: string | null;
  direct_owners: OwnershipFact[];
  upstream_paths: OwnershipPath[];
  conflict: boolean;
  conflicts: OwnershipFact[][];
  message: string;
}

// ---------- FastAPI: POST /api/v1/ask ----------

export const ASK_STATUSES = [
  "answered",
  "unsupported",
  "abstained",
  "refused",
  "bounded_out",
  "unavailable",
] as const;

export type AskStatus = (typeof ASK_STATUSES)[number];

export interface AskRequest {
  question: string;
  as_of?: string;
}

export interface Citation {
  citation_id: string;
  kind: "node" | "relationship";
  // For relationship citations this carries the HOLDS_INTEREST_IN fact plus
  // optional holder_name / held_entity_name. Declared dict[str, Any] upstream.
  details: Record<string, unknown>;
}

export interface AskResponse {
  status: AskStatus;
  answer: string;
  resolved_entities: EntityMatch[];
  citations: Citation[];
  conflicts: Record<string, unknown>[][];
}

// ---------- FastAPI: GET /ready ----------

export interface FastApiReadiness {
  status: "ok" | "unavailable";
  checks: Record<string, boolean>;
}

// ---------- Django: GET /api/v1/ledger/entities/{entity_uid} ----------

export interface LedgerProvenance {
  source_file: string;
  line_number: number;
  ingestion_status: string;
  reason: string;
}

export interface LedgerEntity {
  entity_uid: string;
  legal_name: string;
  legal_name_ar: string | null;
  jurisdiction: string;
  registration_no: string;
  incorporation_date: string;
  status: string;
  status_as_of: string;
  provenance: LedgerProvenance | null;
}

export interface LedgerFiling {
  filing_uid: string;
  filing_type: string;
  filed_on: string;
  source_registry: string;
  asserts_about: string;
  supersedes: string | null;
  provenance: LedgerProvenance | null;
}

export interface LedgerInterest {
  relationship: "HOLDS_INTEREST_IN";
  holder_type: EntityType;
  holder_uid: string;
  held_entity_uid: string;
  bps: number;
  valid_from: string;
  valid_to: string | null;
  filing_uid: string | null;
  provenance: LedgerProvenance | null;
}

export interface LedgerResponse {
  entity: LedgerEntity;
  filings: LedgerFiling[];
  ownership_interests: LedgerInterest[];
}

// ---------- Django: GET /api/v1/audit/{request_id} ----------

export interface AuditRecord {
  request_id: string;
  question: string;
  as_of: string | null;
  generated_cypher: string | null;
  cypher_executed: boolean;
  model_name: string;
  model_digest: string;
  schema_version: string;
  resolved_entities: Record<string, unknown>[];
  citations: Record<string, unknown>[];
  outcome: AskStatus;
  final_response: unknown;
  failure_reason: string;
  created_at: string;
}

// ---------- Web BFF: GET /api/status ----------

export type OverallServiceState = "ready" | "degraded" | "unavailable";

export interface ServiceProbe {
  reachable: boolean;
  ready: boolean;
  httpStatus: number | null;
  // Dependency checks exactly as the backend reported them.
  checks: Record<string, boolean | string>;
}

export interface ServiceStatus {
  overall: OverallServiceState;
  fastapi: ServiceProbe;
  django: ServiceProbe;
  checkedAt: string;
}
