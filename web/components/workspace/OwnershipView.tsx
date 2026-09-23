import { bpsToPercent, formatBps, formatValidity } from "@/lib/format";
import { buildNameIndex, findLedgerInterest, sumBps, type NodeInfo } from "@/lib/ownership";
import type { LedgerInterest, OwnershipFact, OwnershipPath, OwnershipResponse } from "@/types/api";
import { ConflictPanel } from "../ConflictPanel";
import { EntityTypeBadge } from "../EntityTypeBadge";
import { Badge, Notice } from "../ui";
import { ErrorDetails } from "../ErrorNotice";

/** Renders one ownership response exactly as returned: holders, chains, conflicts and cycles. */
export function OwnershipView({
  ownership,
  ledgerInterests,
}: {
  ownership: OwnershipResponse;
  ledgerInterests?: LedgerInterest[];
}) {
  const names = buildNameIndex(ownership.upstream_paths);
  const indirectPaths = ownership.upstream_paths.filter((path) => path.relationships.length > 1);
  const cyclePaths = ownership.upstream_paths.filter((path) => path.cycle);
  const isEmpty = ownership.direct_owners.length === 0 && ownership.upstream_paths.length === 0;

  if (isEmpty) {
    return (
      <Notice
        tone="neutral"
        role="status"
        title={
          ownership.temporal_mode === "current"
            ? "No ownership records were found for this entity."
            : `No ownership records were found for this entity on ${ownership.as_of ?? "the selected date"}.`
        }
      >
        <p>
          {ownership.temporal_mode === "current"
            ? "Try Historical ownership to check a past date."
            : "Try a different date, or switch back to Current ownership."}
        </p>
        <p className="mt-1">
          This means Watheeq holds no ownership record for this view. It does not mean the entity has no owners.
        </p>
        <ErrorDetails message={ownership.message} status={null} />
      </Notice>
    );
  }

  const directTotal = sumBps(ownership.direct_owners);

  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Direct owners" value={ownership.direct_owners.length} />
        <Stat label="Ownership chains" value={ownership.upstream_paths.length} />
        <Stat label="Conflicts" value={ownership.conflicts.length} tone={ownership.conflicts.length ? "warning" : undefined} />
        <Stat label="Circular chains" value={cyclePaths.length} tone={cyclePaths.length ? "warning" : undefined} />
      </dl>

      {ownership.conflicts.length > 0 && (
        <ConflictPanel
          groups={ownership.conflicts.map((group) => group.map((fact) => ({ ...fact })))}
          nameFor={(uid) => names.get(uid)?.displayName ?? null}
          provenanceFor={(fact) => findLedgerInterest(ledgerInterests, fact)?.provenance ?? null}
        />
      )}

      <section aria-labelledby="direct-heading">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h3 id="direct-heading" className="text-sm font-semibold uppercase tracking-wide text-slate-600">
            Direct owners
          </h3>
          <p className="text-sm text-slate-600">
            Total of recorded direct holdings: {bpsToPercent(directTotal)} ({formatBps(directTotal)}), shown exactly as
            recorded.
          </p>
        </div>
        <ul className="mt-3 space-y-3">
          {ownership.direct_owners.map((fact) => (
            <DirectHolderRow
              key={fact.citation_id}
              fact={fact}
              holder={names.get(fact.holder_uid)}
              ledgerInterest={findLedgerInterest(ledgerInterests, fact)}
            />
          ))}
        </ul>
      </section>

      {(indirectPaths.length > 0 || cyclePaths.length > 0) && (
        <section aria-labelledby="chains-heading">
          <h3 id="chains-heading" className="text-sm font-semibold uppercase tracking-wide text-slate-600">
            Ownership chains
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            How ownership reaches this entity through other companies, read from left to right. These show recorded
            holdings only; they don&apos;t establish who ultimately owns or controls the entity.
          </p>
          <ul className="mt-3 space-y-3">
            {ownership.upstream_paths
              .filter((path) => path.relationships.length > 1 || path.cycle)
              .map((path, index) => (
                <PathRow key={index} path={path} />
              ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "warning" }) {
  return (
    <div className={`rounded-lg border p-3 ${tone ? "border-amber-200 bg-amber-50" : "border-line bg-white"}`}>
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-0.5 text-2xl font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

function DirectHolderRow({
  fact,
  holder,
  ledgerInterest,
}: {
  fact: OwnershipFact;
  holder: NodeInfo | undefined;
  ledgerInterest: LedgerInterest | null;
}) {
  const selfHolding = fact.holder_uid === fact.held_entity_uid;
  return (
    <li className="rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <EntityTypeBadge type={fact.holder_type} />
            {selfHolding && <Badge tone="warning">Holds shares in itself (circular)</Badge>}
          </div>
          <p dir="auto" className="mt-1.5 break-anywhere font-semibold text-slate-900">
            {holder?.displayName ?? fact.holder_uid}
          </p>
          <p className="font-mono text-xs text-slate-600">{fact.holder_uid}</p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold text-blue-800">{bpsToPercent(fact.bps)}</p>
          <p className="text-xs text-slate-600">{formatBps(fact.bps)}</p>
        </div>
      </div>
      <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm text-slate-700 sm:grid-cols-2">
        <div>
          <dt className="inline text-slate-600">Valid: </dt>
          <dd className="inline">{formatValidity(fact.valid_from, fact.valid_to)}</dd>
        </div>
        <div>
          <dt className="inline text-slate-600">Filing: </dt>
          <dd className="inline font-mono">{fact.filing_uid ?? "none recorded"}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="inline text-slate-600">Source record: </dt>
          <dd className="inline break-anywhere font-mono">
            {ledgerInterest?.provenance
              ? `${ledgerInterest.provenance.source_file}:${ledgerInterest.provenance.line_number} (${ledgerInterest.provenance.ingestion_status})`
              : "no exactly matching official record"}
          </dd>
        </div>
      </dl>
      <details className="mt-2 text-xs">
        <summary className="cursor-pointer text-slate-600 hover:text-slate-800">Evidence ID</summary>
        <p className="mt-1 break-anywhere font-mono text-slate-600">{fact.citation_id}</p>
      </details>
    </li>
  );
}

function PathRow({ path }: { path: OwnershipPath }) {
  return (
    <li className="rounded-lg border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge>{path.relationships.length} {path.relationships.length === 1 ? "step" : "steps"}</Badge>
        {path.cycle && <Badge tone="warning">Circular — an entity appears twice in this chain</Badge>}
      </div>
      <ol className="flex flex-col gap-2 md:flex-row md:flex-wrap md:items-center">
        {path.nodes.map((node, index) => {
          const edge = path.relationships[index];
          return (
            <li key={`${node.canonical_id}-${index}`} className="flex flex-col gap-2 md:flex-row md:items-center">
              <div className="min-w-0 rounded-md border border-line bg-slate-50 px-3 py-2">
                <p dir="auto" className="break-anywhere text-sm font-medium text-slate-900">
                  {node.display_name}
                </p>
                <p className="font-mono text-xs text-slate-600">{node.canonical_id}</p>
              </div>
              {edge && (
                <div className="px-1 text-sm text-slate-700" aria-label={`holds ${bpsToPercent(edge.bps)} in`}>
                  <span className="md:hidden">↓ </span>
                  <span className="font-semibold text-blue-800">{bpsToPercent(edge.bps)}</span>
                  <span className="hidden md:inline"> →</span>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </li>
  );
}
