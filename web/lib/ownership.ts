// Pure lookup helpers for ownership evidence. None of these alter or reconcile facts.

import type { EntityType, LedgerInterest, OwnershipPath } from "@/types/api";

export interface NodeInfo {
  type: EntityType;
  displayName: string;
}

/** Display names come only from nodes the backend returned in upstream paths. */
export function buildNameIndex(paths: OwnershipPath[]): Map<string, NodeInfo> {
  const index = new Map<string, NodeInfo>();
  for (const path of paths) {
    for (const node of path.nodes) {
      index.set(node.canonical_id, { type: node.type, displayName: node.display_name });
    }
  }
  return index;
}

interface FactLike {
  holder_uid?: unknown;
  held_entity_uid?: unknown;
  bps?: unknown;
  valid_from?: unknown;
  valid_to?: unknown;
  filing_uid?: unknown;
}

/**
 * Find the authoritative ledger row for one graph ownership fact by exact field equality.
 * Returns null rather than guessing when no row matches exactly.
 */
export function findLedgerInterest(interests: LedgerInterest[] | undefined, fact: FactLike): LedgerInterest | null {
  if (!interests) return null;
  return (
    interests.find(
      (interest) =>
        interest.holder_uid === fact.holder_uid &&
        interest.held_entity_uid === fact.held_entity_uid &&
        interest.bps === fact.bps &&
        interest.valid_from === fact.valid_from &&
        (interest.valid_to ?? null) === (fact.valid_to ?? null) &&
        (interest.filing_uid ?? null) === (fact.filing_uid ?? null),
    ) ?? null
  );
}

/** Arithmetic sum of returned bps, reported as-is (it may be above or below 10,000). */
export function sumBps(facts: { bps: number }[]): number {
  return facts.reduce((total, fact) => total + fact.bps, 0);
}
