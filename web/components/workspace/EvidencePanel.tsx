import { bpsToPercent, entityTypeLabel, formatBps, formatValidity } from "@/lib/format";
import type { LedgerProvenance, LedgerResponse } from "@/types/api";
import { Badge, Field } from "../ui";

/** Registry profile from the authoritative Django/PostgreSQL ledger. */
export function RegistryProfile({ ledger }: { ledger: LedgerResponse }) {
  const { entity } = ledger;
  return (
    <dl className="grid gap-3">
      <Field label="Entity ID" mono>
        {entity.entity_uid}
      </Field>
      <Field label="Legal name">
        <span dir="auto">{entity.legal_name}</span>
      </Field>
      {entity.legal_name_ar && (
        <Field label="Arabic legal name">
          <span dir="rtl" lang="ar">
            {entity.legal_name_ar}
          </span>
        </Field>
      )}
      <Field label="Jurisdiction">{entity.jurisdiction}</Field>
      <Field label="Registration no." mono>
        {entity.registration_no}
      </Field>
      <Field label="Incorporated">{entity.incorporation_date}</Field>
      <Field label="Status">
        {entity.status} <span className="text-slate-600">(as of {entity.status_as_of})</span>
      </Field>
      <Field label="Record source">
        <ProvenanceText provenance={entity.provenance} />
      </Field>
    </dl>
  );
}

/** Filings and every ledger ownership assertion that mentions this entity, with source lines. */
export function LedgerEvidence({ ledger }: { ledger: LedgerResponse }) {
  const uid = ledger.entity.entity_uid;
  const heldIn = ledger.ownership_interests.filter((interest) => interest.held_entity_uid === uid);
  const heldBy = ledger.ownership_interests.filter(
    (interest) => interest.holder_uid === uid && interest.held_entity_uid !== uid,
  );

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-slate-900">Filings ({ledger.filings.length})</h3>
        {ledger.filings.length === 0 ? (
          <p className="mt-1 text-sm text-slate-600">No filings are recorded for this entity.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {ledger.filings.map((filing) => (
              <li key={filing.filing_uid} className="rounded-md border border-line p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[13px] font-semibold">{filing.filing_uid}</span>
                  <Badge>{filing.filing_type}</Badge>
                  {filing.supersedes && <Badge tone="info">Supersedes {filing.supersedes}</Badge>}
                </div>
                <p className="mt-1 text-sm text-slate-700">
                  Filed {filing.filed_on} · {filing.source_registry} · about{" "}
                  <span className="font-mono">{filing.asserts_about}</span>
                </p>
                <p className="mt-0.5 text-sm text-slate-600">
                  Source record: <ProvenanceText provenance={filing.provenance} />
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <InterestList
        title={`Recorded owners of this entity, all dates (${heldIn.length})`}
        interests={heldIn}
        counterpart="holder"
      />
      {heldBy.length > 0 && (
        <InterestList
          title={`Companies this entity holds interests in, all dates (${heldBy.length})`}
          interests={heldBy}
          counterpart="held"
        />
      )}
      <p className="text-sm text-slate-600">
        These lists include every record across all dates. The ownership view above shows only the records that apply
        to the selected current or historical view.
      </p>
    </div>
  );
}

function InterestList({
  title,
  interests,
  counterpart,
}: {
  title: string;
  interests: LedgerResponse["ownership_interests"];
  counterpart: "holder" | "held";
}) {
  return (
    <div>
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      {interests.length === 0 ? (
        <p className="mt-1 text-sm text-slate-600">None recorded.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {interests.map((interest, index) => (
            <li key={index} className="rounded-md border border-line p-3 text-sm text-slate-700">
              <p className="text-base">
                <span className="font-mono font-semibold">
                  {counterpart === "holder" ? interest.holder_uid : interest.held_entity_uid}
                </span>{" "}
                <span className="text-slate-600">
                  ({counterpart === "holder" ? entityTypeLabel(interest.holder_type) : entityTypeLabel("LegalEntity")})
                </span>
                {" · "}
                <span className="font-semibold">{bpsToPercent(interest.bps)}</span>{" "}
                <span className="text-slate-600">{formatBps(interest.bps)}</span>
              </p>
              <p className="mt-1">{formatValidity(interest.valid_from, interest.valid_to)}</p>
              <p className="mt-0.5">
                Filing <span className="font-mono">{interest.filing_uid ?? "none recorded"}</span> · Source record:{" "}
                <ProvenanceText provenance={interest.provenance} />
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ProvenanceText({ provenance }: { provenance: LedgerProvenance | null }) {
  if (!provenance) return <span className="text-slate-600">No source record</span>;
  return (
    <span className="break-anywhere">
      <span className="font-mono">
        {provenance.source_file}:{provenance.line_number}
      </span>{" "}
      <span className="text-slate-600">({provenance.ingestion_status})</span>
      {provenance.reason && <span className="text-slate-600"> — {provenance.reason}</span>}
    </span>
  );
}
