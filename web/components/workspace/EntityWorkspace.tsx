"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { getLedger, getOwnership, type ApiError } from "@/lib/api";
import type { LedgerResponse, OwnershipResponse } from "@/types/api";
import { EntityTypeBadge } from "../EntityTypeBadge";
import { ErrorNotice } from "../ErrorNotice";
import { PageHeader } from "../PageHeader";
import { Notice, Panel, SkeletonRows } from "../ui";
import { LedgerEvidence, RegistryProfile } from "./EvidencePanel";
import { OwnershipModeControl } from "./OwnershipModeControl";
import { OwnershipView } from "./OwnershipView";

type Loadable<T> = { kind: "loading" } | { kind: "ok"; data: T } | { kind: "error"; error: ApiError };

/**
 * Legal-entity workspace. Ownership (FastAPI, Neo4j projection) and the ledger
 * (Django, PostgreSQL) load concurrently and fail independently.
 */
export function EntityWorkspace({ entityUid, initialAsOf }: { entityUid: string; initialAsOf: string | null }) {
  const [asOf, setAsOf] = useState<string | null>(initialAsOf);
  const [ownership, setOwnership] = useState<Loadable<OwnershipResponse>>({ kind: "loading" });
  const [ledger, setLedger] = useState<Loadable<LedgerResponse>>({ kind: "loading" });
  const ownershipRequest = useRef(0);

  const loadOwnership = useCallback(
    async (date: string | null) => {
      const requestNumber = ++ownershipRequest.current;
      setOwnership({ kind: "loading" });
      const result = await getOwnership(entityUid, date);
      // Discard stale responses when the analyst switched dates mid-request.
      if (requestNumber !== ownershipRequest.current) return;
      setOwnership(result.ok ? { kind: "ok", data: result.data } : { kind: "error", error: result.error });
    },
    [entityUid],
  );

  const loadLedger = useCallback(async () => {
    setLedger({ kind: "loading" });
    const result = await getLedger(entityUid);
    setLedger(result.ok ? { kind: "ok", data: result.data } : { kind: "error", error: result.error });
  }, [entityUid]);

  useEffect(() => {
    const timer = setTimeout(() => loadLedger(), 0);
    return () => clearTimeout(timer);
  }, [loadLedger]);

  useEffect(() => {
    const timer = setTimeout(() => loadOwnership(asOf), 0);
    return () => clearTimeout(timer);
  }, [asOf, loadOwnership]);

  function changeMode(next: string | null) {
    setAsOf(next);
    // Keep the mode in the URL so reloads and shared links preserve it.
    const url = `/entities/${encodeURIComponent(entityUid)}${next ? `?as_of=${next}` : ""}`;
    window.history.replaceState(null, "", url);
  }

  const ledgerData = ledger.kind === "ok" ? ledger.data : null;
  const bothNotFound =
    ownership.kind === "error" &&
    ownership.error.kind === "not_found" &&
    ledger.kind === "error" &&
    ledger.error.kind === "not_found";

  if (bothNotFound) {
    return (
      <>
        <PageHeader title="Entity not found" eyebrow={<Breadcrumb label={entityUid} />} />
        <Notice tone="neutral" title={`Watheeq has no company with the ID “${entityUid}”`}>
          <p>
            Ownership pages exist for companies (legal entities) only. To explore a person, search for them and use
            Ask Watheeq.
          </p>
          <p className="mt-2">
            <Link href="/" className="font-semibold text-blue-700 hover:underline">
              Back to Entity Search
            </Link>
          </p>
        </Notice>
      </>
    );
  }

  const title = ledgerData?.entity.legal_name ?? entityUid;

  return (
    <>
      <PageHeader
        eyebrow={<Breadcrumb label={title} />}
        title={<span dir="auto">{title}</span>}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-mono">{entityUid}</span>
            {ledgerData && <span>{ledgerData.entity.jurisdiction}</span>}
            <EntityTypeBadge type="LegalEntity" />
            {ledgerData && <span>Status: {ledgerData.entity.status}</span>}
          </span>
        }
        actions={
          <>
            <a
              href="#evidence"
              className="inline-flex min-h-10 items-center rounded-lg border border-line bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              View evidence
            </a>
            <Link
              href={`/ask?entity=${encodeURIComponent(entityUid)}`}
              className="inline-flex min-h-10 items-center rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
            >
              Ask about this entity
            </Link>
          </>
        }
      />

      <div className="mb-5">
        <OwnershipModeControl asOf={asOf} onChange={changeMode} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px] 2xl:grid-cols-[minmax(0,1fr)_440px]">
        <Panel
          title={asOf ? `Ownership on ${asOf}` : "Current ownership"}
          description={
            asOf
              ? "Ownership as it was recorded on this date. Records that start or end on this date are included."
              : "The latest recorded ownership: records that are still in force."
          }
        >
          {ownership.kind === "loading" && <SkeletonRows rows={4} />}
          {ownership.kind === "error" && (
            <ErrorNotice
              error={ownership.error}
              context="Ownership records couldn't be loaded."
              onRetry={() => loadOwnership(asOf)}
            />
          )}
          {ownership.kind === "ok" && (
            <OwnershipView ownership={ownership.data} ledgerInterests={ledgerData?.ownership_interests} />
          )}
        </Panel>

        <div className="space-y-6 xl:sticky xl:top-8 xl:h-fit">
          <Panel title="Registry profile" description="The official registry record for this company.">
            {ledger.kind === "loading" && <SkeletonRows rows={3} />}
            {ledger.kind === "error" && (
              <ErrorNotice error={ledger.error} context="The registry profile couldn't be loaded." onRetry={loadLedger} />
            )}
            {ledgerData && <RegistryProfile ledger={ledgerData} />}
          </Panel>
        </div>
      </div>

      <Panel
        id="evidence"
        className="mt-6 scroll-mt-24"
        title="Evidence & provenance"
        description="The filings and ownership records behind this page, each traced to the exact source file and line it came from."
      >
        {ledger.kind === "loading" && <SkeletonRows rows={3} />}
        {ledger.kind === "error" && (
          <ErrorNotice error={ledger.error} context="Filings and source records couldn't be loaded." onRetry={loadLedger} />
        )}
        {ledgerData && <LedgerEvidence ledger={ledgerData} />}
      </Panel>
    </>
  );
}

function Breadcrumb({ label }: { label: string }) {
  return (
    <nav aria-label="Breadcrumb" className="break-anywhere">
      <Link href="/" className="hover:text-slate-700 hover:underline">
        Entity Search
      </Link>
      <span className="mx-1.5">/</span>
      <span dir="auto">{label}</span>
    </nav>
  );
}
