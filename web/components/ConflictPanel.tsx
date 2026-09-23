import { bpsToPercent, formatBps, formatValidity, textField } from "@/lib/format";
import type { LedgerProvenance } from "@/types/api";
import { Badge } from "./ui";

type Fact = Record<string, unknown>;

/**
 * Shows each group of competing ownership assertions side by side.
 * The frontend never picks a winner or merges them.
 */
export function ConflictPanel({
  groups,
  nameFor,
  provenanceFor,
}: {
  groups: Fact[][];
  nameFor?: (uid: string) => string | null;
  provenanceFor?: (fact: Fact) => LedgerProvenance | null;
}) {
  if (groups.length === 0) return null;

  return (
    <section aria-labelledby="conflicts-heading" className="rounded-xl border border-amber-300 bg-amber-50/60 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h3 id="conflicts-heading" className="text-lg font-semibold text-amber-950">
          Conflicting records
        </h3>
        <Badge tone="warning">
          {groups.length} {groups.length === 1 ? "conflict" : "conflicts"}
        </Badge>
      </div>
      <p className="mt-1 text-sm text-amber-900">
        Watheeq has more than one record for the same owner and entity. All of them are shown below with their dates
        and filings. Watheeq does not pick one over another.
      </p>

      <div className="mt-4 space-y-4">
        {groups.map((group, groupIndex) => {
          const holderUid = textField(group[0] ?? {}, "holder_uid") ?? "unknown holder";
          const heldUid = textField(group[0] ?? {}, "held_entity_uid") ?? "unknown entity";
          const holderName = textField(group[0] ?? {}, "holder_name") ?? nameFor?.(holderUid) ?? null;
          const heldName = textField(group[0] ?? {}, "held_entity_name") ?? nameFor?.(heldUid) ?? null;
          return (
            <div key={groupIndex} className="rounded-lg border border-amber-200 bg-white p-4">
              <p className="break-anywhere text-sm font-semibold text-slate-900">
                <span dir="auto">{holderName ?? holderUid}</span>{" "}
                <span className="font-mono text-xs font-normal text-slate-600">{holderUid}</span>
                <span className="mx-2 text-slate-500">→</span>
                <span dir="auto">{heldName ?? heldUid}</span>{" "}
                <span className="font-mono text-xs font-normal text-slate-600">{heldUid}</span>
              </p>
              <ol className="mt-3 grid gap-3 md:grid-cols-2">
                {group.map((fact, factIndex) => (
                  <ConflictAssertion
                    key={textField(fact, "citation_id") ?? factIndex}
                    label={`Record ${String.fromCharCode(65 + factIndex)}`}
                    fact={fact}
                    provenance={provenanceFor?.(fact) ?? null}
                  />
                ))}
              </ol>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ConflictAssertion({
  label,
  fact,
  provenance,
}: {
  label: string;
  fact: Fact;
  provenance: LedgerProvenance | null;
}) {
  const bps = typeof fact.bps === "number" ? fact.bps : null;
  const validFrom = textField(fact, "valid_from");
  const validTo = textField(fact, "valid_to");
  const filing = textField(fact, "filing_uid");
  const citationId = textField(fact, "citation_id");
  return (
    <li className="rounded-md border border-line bg-slate-50 p-3 text-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900">
        {bps !== null ? bpsToPercent(bps) : "—"}{" "}
        {bps !== null && <span className="text-xs font-normal text-slate-600">({formatBps(bps)})</span>}
      </p>
      <dl className="mt-2 space-y-1 text-slate-700">
        {validFrom && (
          <div>
            <dt className="inline text-slate-600">Valid: </dt>
            <dd className="inline">{formatValidity(validFrom, validTo)}</dd>
          </div>
        )}
        <div>
          <dt className="inline text-slate-600">Filing: </dt>
          <dd className="inline font-mono text-[13px]">{filing ?? "none recorded"}</dd>
        </div>
        {provenance && (
          <div>
            <dt className="inline text-slate-600">Source record: </dt>
            <dd className="inline break-anywhere font-mono text-[13px]">
              {provenance.source_file}:{provenance.line_number}
            </dd>
          </div>
        )}
        {citationId && (
          <div>
            <dt className="text-slate-600">Evidence ID</dt>
            <dd className="break-anywhere font-mono text-xs text-slate-600">{citationId}</dd>
          </div>
        )}
      </dl>
    </li>
  );
}
