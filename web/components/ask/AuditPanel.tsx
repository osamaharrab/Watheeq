"use client";

import { useState } from "react";
import type { ApiError } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { OUTCOMES } from "@/lib/outcomes";
import type { AskResponse, AuditRecord } from "@/types/api";
import { ErrorNotice } from "../ErrorNotice";
import { Button, Field, Notice, Spinner } from "../ui";
import { OutcomeBadge } from "./AskResult";

export type AuditState =
  | { kind: "idle" }
  | { kind: "no_request_id" }
  | { kind: "loading" }
  | { kind: "ok"; record: AuditRecord }
  | { kind: "error"; error: ApiError };

/**
 * Evidence & audit trail for one Ask request.
 * Business-facing facts come first; implementation details sit behind a disclosure,
 * and generated Cypher is only rendered after an explicit click.
 */
export function AuditPanel({
  requestId,
  response,
  audit,
  onRetry,
}: {
  requestId: string | null;
  response: AskResponse | null;
  audit: AuditState;
  onRetry: () => void;
}) {
  if (!response) {
    return (
      <p className="text-sm text-slate-600">
        Ask a question to see its request ID, outcome and the permanent audit record Watheeq keeps for it.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <dl className="grid gap-4">
        <Field label="Request ID" mono>
          {requestId ?? "Not returned by the service"}
        </Field>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-600">Outcome</dt>
          <dd className="mt-1">
            <OutcomeBadge status={response.status} />
          </dd>
        </div>
        <Field label="Conflicts">
          {response.conflicts.length === 0
            ? "No conflicts found"
            : `${response.conflicts.length} ${response.conflicts.length === 1 ? "conflict" : "conflicts"} found`}
        </Field>
        <Field label="Evidence">
          {response.citations.length === 0
            ? "No evidence citations returned"
            : `${response.citations.length} evidence ${response.citations.length === 1 ? "citation" : "citations"}`}
        </Field>
      </dl>

      <div className="border-t border-line pt-4">
        <h3 className="text-sm font-semibold text-slate-900">Audit record</h3>
        <div className="mt-2">
          {audit.kind === "no_request_id" && (
            <Notice tone="warning" title="The audit record can't be shown here">
              The response didn&apos;t include a request ID, so its audit record can&apos;t be looked up.
            </Notice>
          )}
          {audit.kind === "loading" && <Spinner label="Loading the audit record…" />}
          {audit.kind === "error" && (
            <ErrorNotice error={audit.error} context="The audit record couldn't be loaded. Your result is unaffected." onRetry={onRetry} />
          )}
          {audit.kind === "ok" && <AuditRecordView record={audit.record} response={response} />}
        </div>
      </div>
    </div>
  );
}

function AuditRecordView({ record, response }: { record: AuditRecord; response: AskResponse }) {
  const [showCypher, setShowCypher] = useState(false);
  const outcomeMismatch = record.outcome !== response.status;

  return (
    <div className="space-y-4">
      <dl className="grid gap-3">
        <Field label="Recorded at">{formatTimestamp(record.created_at)}</Field>
        <Field label="Outcome recorded">
          {OUTCOMES[record.outcome]?.label ?? record.outcome}
        </Field>
        <Field label="As-of date">{record.as_of ?? "None (current ownership)"}</Field>
        <Field label="Evidence citations recorded">{record.citations.length}</Field>
      </dl>
      {outcomeMismatch && (
        <Notice tone="danger" title="The audit record doesn't match this result">
          The audit trail records “{record.outcome}” but the response was “{response.status}”.
        </Notice>
      )}

      <details className="group rounded-lg border border-line">
        <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
          Technical details
        </summary>
        <div className="space-y-3 border-t border-line px-3 py-3">
          <dl className="grid gap-3">
            <Field label="Model">{record.model_name}</Field>
            <Field label="Model digest" mono>
              {record.model_digest}
            </Field>
            <Field label="Schema version">{record.schema_version}</Field>
            <Field label="Cypher executed">{record.cypher_executed ? "Yes" : "No"}</Field>
            <Field label="Failure reason">{record.failure_reason || "None recorded"}</Field>
          </dl>
          {record.generated_cypher ? (
            <div>
              <Button variant="secondary" onClick={() => setShowCypher((value) => !value)}>
                {showCypher ? "Hide generated Cypher" : "View generated Cypher"}
              </Button>
              {showCypher && (
                <pre
                  data-testid="generated-cypher"
                  className="mt-2 max-h-80 overflow-auto rounded-md bg-navy-950 p-3 font-mono text-xs leading-relaxed text-slate-100"
                >
                  {record.generated_cypher}
                </pre>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-600">No Cypher was generated for this request.</p>
          )}
        </div>
      </details>
    </div>
  );
}
