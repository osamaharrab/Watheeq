"use client";

import { useState } from "react";
import { getLedger, type ApiError } from "@/lib/api";
import { bpsToPercent, formatBps, formatValidity, textField } from "@/lib/format";
import { findLedgerInterest } from "@/lib/ownership";
import type { Citation, LedgerFiling, LedgerInterest } from "@/types/api";
import { ErrorNotice } from "../ErrorNotice";
import { EntityTypeBadge } from "../EntityTypeBadge";
import { Button, Spinner } from "../ui";
import { ProvenanceText } from "../workspace/EvidencePanel";

export function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <section aria-labelledby="citations-heading">
      <h3 id="citations-heading" className="text-sm font-semibold text-slate-900">
        Evidence ({citations.length})
      </h3>
      <p className="mt-0.5 text-xs text-slate-600">
        The ownership records this answer is based on. Open one to see the official source record and filing.
      </p>
      <ol className="mt-3 space-y-3">
        {citations.map((citation, index) => (
          <CitationCard key={citation.citation_id} citation={citation} number={index + 1} />
        ))}
      </ol>
    </section>
  );
}

type Inspection =
  | { kind: "closed" }
  | { kind: "loading" }
  | { kind: "found"; interest: LedgerInterest; filing: LedgerFiling | null }
  | { kind: "no_match" }
  | { kind: "error"; error: ApiError };

function CitationCard({ citation, number }: { citation: Citation; number: number }) {
  const [inspection, setInspection] = useState<Inspection>({ kind: "closed" });
  const details = citation.details;
  const isRelationship = citation.kind === "relationship";
  const holderUid = textField(details, "holder_uid");
  const heldUid = textField(details, "held_entity_uid");
  const bps = typeof details.bps === "number" ? details.bps : null;
  const validFrom = textField(details, "valid_from");

  async function inspect() {
    if (!heldUid) return;
    setInspection({ kind: "loading" });
    // The ledger endpoint lists every assertion held in the entity, so look up by held entity.
    const result = await getLedger(heldUid);
    if (!result.ok) {
      setInspection({ kind: "error", error: result.error });
      return;
    }
    const interest = findLedgerInterest(result.data.ownership_interests, details);
    if (!interest) {
      setInspection({ kind: "no_match" });
      return;
    }
    const filing = result.data.filings.find((item) => item.filing_uid === interest.filing_uid) ?? null;
    setInspection({ kind: "found", interest, filing });
  }

  return (
    <li id={`citation-${number}`} className="scroll-mt-24 rounded-lg border border-line bg-slate-50/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 gap-3">
          <span className="mt-0.5 shrink-0 rounded bg-blue-100 px-1.5 font-mono text-xs font-semibold text-blue-800">
            [{number}]
          </span>
          <div className="min-w-0">
            {isRelationship && holderUid && heldUid ? (
              <>
                <p className="break-anywhere text-sm font-semibold text-slate-900">
                  <span dir="auto">{textField(details, "holder_name") ?? holderUid}</span>
                  <span className="mx-1.5 text-slate-500">→</span>
                  <span dir="auto">{textField(details, "held_entity_name") ?? heldUid}</span>
                </p>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600">
                  {textField(details, "holder_type") && <EntityTypeBadge type={String(details.holder_type)} />}
                  <span className="font-mono">
                    {holderUid} → {heldUid}
                  </span>
                  {bps !== null && (
                    <span>
                      <span className="font-semibold text-blue-800">{bpsToPercent(bps)}</span> ({formatBps(bps)})
                    </span>
                  )}
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  {validFrom && formatValidity(validFrom, textField(details, "valid_to"))} · Filing{" "}
                  <span className="font-mono">{textField(details, "filing_uid") ?? "none recorded"}</span>
                </p>
              </>
            ) : (
              <GenericDetails details={details} />
            )}
          </div>
        </div>
        {isRelationship && heldUid && inspection.kind === "closed" && (
          <Button variant="ghost" onClick={inspect} className="px-2 py-1">
            View source record
          </Button>
        )}
      </div>

      <details className="mt-2 text-xs">
        <summary className="cursor-pointer text-slate-600 hover:text-slate-700">Evidence ID</summary>
        <p className="mt-1 break-anywhere font-mono text-slate-600">{citation.citation_id}</p>
      </details>

      {inspection.kind === "loading" && (
        <div className="mt-3">
          <Spinner label="Checking Watheeq's records…" />
        </div>
      )}
      {inspection.kind === "error" && (
        <div className="mt-3">
          <ErrorNotice error={inspection.error} context="The source record couldn't be loaded." onRetry={inspect} />
        </div>
      )}
      {inspection.kind === "no_match" && (
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          No official record matched this evidence exactly, so no source is shown rather than a guess.
        </p>
      )}
      {inspection.kind === "found" && (
        <div className="mt-3 rounded-md border border-line bg-white p-3 text-xs text-slate-700">
          <p className="font-semibold text-slate-900">Official source record</p>
          <p className="mt-1">
            Ownership record: <ProvenanceText provenance={inspection.interest.provenance} />
          </p>
          {inspection.filing ? (
            <p className="mt-1">
              Filing <span className="font-mono">{inspection.filing.filing_uid}</span> ({inspection.filing.filing_type},
              filed {inspection.filing.filed_on}, {inspection.filing.source_registry}
              {inspection.filing.supersedes ? `, supersedes ${inspection.filing.supersedes}` : ""}):{" "}
              <ProvenanceText provenance={inspection.filing.provenance} />
            </p>
          ) : (
            <p className="mt-1 text-slate-600">No filing is linked to this ownership record.</p>
          )}
        </div>
      )}
    </li>
  );
}

function GenericDetails({ details }: { details: Record<string, unknown> }) {
  return (
    <dl className="grid gap-1 text-xs">
      {Object.entries(details).map(([key, value]) => (
        <div key={key} className="flex min-w-0 gap-2">
          <dt className="text-slate-600">{key}</dt>
          <dd className="break-anywhere font-mono text-slate-800">
            {typeof value === "object" ? JSON.stringify(value) : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}
