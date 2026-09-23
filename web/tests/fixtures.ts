// Test-only payloads shaped like real backend responses. Never imported by application code.
import type { AskResponse, AuditRecord, EntityMatch } from "@/types/api";

export const legalEntityA: EntityMatch = {
  type: "LegalEntity",
  canonical_id: "LE-T1",
  display_name: "Shared Name Holdings",
  metadata: { jurisdiction: "JO", registration_no: "REG-1" },
  match_method: "exact",
};
export const legalEntityB: EntityMatch = { ...legalEntityA, canonical_id: "LE-T2", metadata: { jurisdiction: "AE" } };
export const person: EntityMatch = {
  type: "NaturalPerson",
  canonical_id: "NP-T1",
  display_name: "Shared Name Holdings",
  metadata: { nationality: "GB" },
  match_method: "exact",
};

const fact = {
  relationship: "HOLDS_INTEREST_IN",
  holder_type: "LegalEntity",
  holder_uid: "LE-H",
  held_entity_uid: "LE-T1",
  holder_name: "Holder Co",
  held_entity_name: "Target Co",
  filing_uid: "FL-1",
};

export const answered: AskResponse = {
  status: "answered",
  answer: "Ownership relationships: Holder Co (LE-H) (2500 bps) [1].",
  resolved_entities: [legalEntityA],
  citations: [
    {
      citation_id: "HOLDS_INTEREST_IN:LegalEntity:LE-H:LE-T1:2500:2020-01-01:null:FL-1",
      kind: "relationship",
      details: { ...fact, bps: 2500, valid_from: "2020-01-01", valid_to: null },
    },
  ],
  conflicts: [],
};

export const withConflict: AskResponse = {
  ...answered,
  answer: "Conflicting ownership assertions are effective as of 2025-01-01: A [1]; B [2].",
  conflicts: [
    [
      { ...fact, bps: 7000, valid_from: "2010-01-01", valid_to: "2025-01-01", citation_id: "c-a" },
      { ...fact, bps: 2000, valid_from: "2025-01-01", valid_to: null, citation_id: "c-b" },
    ],
  ],
};

export function nonAnswer(status: AskResponse["status"], answer: string): AskResponse {
  return { status, answer, resolved_entities: [], citations: [], conflicts: [] };
}

export const auditRecord: AuditRecord = {
  request_id: "11111111-2222-4333-8444-555555555555",
  question: "Who holds interests in LE-T1?",
  as_of: null,
  generated_cypher: "MATCH (holder)-[rel:HOLDS_INTEREST_IN]->(target) RETURN holder LIMIT 100",
  cypher_executed: true,
  model_name: "local-model",
  model_digest: "digest",
  schema_version: "schema-1",
  resolved_entities: [],
  citations: [{}],
  outcome: "answered",
  final_response: {},
  failure_reason: "",
  created_at: "2026-01-01T00:00:00Z",
};
