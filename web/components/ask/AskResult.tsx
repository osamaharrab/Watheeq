import { Fragment } from "react";
import { OUTCOMES } from "@/lib/outcomes";
import type { AskResponse, AskStatus } from "@/types/api";
import { ConflictPanel } from "../ConflictPanel";
import { EntityTypeBadge } from "../EntityTypeBadge";
import { Badge, Button, Notice } from "../ui";
import { CitationList } from "./CitationList";

export function OutcomeBadge({ status }: { status: AskStatus }) {
  const outcome = OUTCOMES[status];
  return <Badge tone={outcome.tone}>{outcome.label}</Badge>;
}

/** Renders one /ask response according to its business outcome. */
export function AskResult({
  response,
  asOf,
  question,
  onRetry,
}: {
  response: AskResponse;
  asOf: string | null;
  question?: string;
  onRetry?: () => void;
}) {
  const outcome = OUTCOMES[response.status];
  const answered = response.status === "answered";
  // Mirrors the backend rule: a year in the question text needs the structured as-of date.
  const dateTip = response.status === "abstained" && !asOf && /\b(?:19|20)\d{2}\b/.test(question ?? "");

  return (
    <div className="space-y-5" data-testid="ask-result" data-status={response.status}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{answered ? outcome.headline : "Result"}</h2>
          <p className="mt-0.5 text-sm text-slate-600">
            {asOf ? `Ownership as of ${asOf}` : "Current ownership (no date selected)"}
          </p>
        </div>
        <OutcomeBadge status={response.status} />
      </div>

      {answered ? (
        <>
          <p className="max-w-[80ch] break-anywhere text-base leading-relaxed text-slate-900">
            <AnswerWithMarkers answer={response.answer} citationCount={response.citations.length} />
          </p>
          {response.citations.length === 0 && (
            <Notice tone="warning" title="No evidence citations returned">
              Watheeq marked this as answered but returned no evidence, so it is not presented as verified.
            </Notice>
          )}
          <p className="text-sm text-slate-600">{outcome.helper}</p>
        </>
      ) : (
        <div className="space-y-3">
          <Notice
            tone={outcome.tone}
            title={outcome.headline}
            action={
              response.status === "unavailable" && onRetry ? (
                <Button variant="secondary" onClick={onRetry} className="py-1.5">
                  Try again
                </Button>
              ) : undefined
            }
          >
            <p>{outcome.helper}</p>
            {dateTip && (
              <p className="mt-2 font-medium">
                Tip: your question mentions a year. Choose the date in the “As-of date” field and ask again.
              </p>
            )}
          </Notice>
          <TechnicalReason reason={response.answer} />
        </div>
      )}

      {response.conflicts.length > 0 && <ConflictPanel groups={response.conflicts} />}

      {response.resolved_entities.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {response.resolved_entities.length === 1 ? "Entity found" : "Entities found in your question"}
          </h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {response.resolved_entities.map((entity) => (
              <li
                key={`${entity.type}:${entity.canonical_id}`}
                className="flex min-w-0 items-center gap-2 rounded-md border border-line bg-slate-50 px-2.5 py-1.5 text-sm"
              >
                <EntityTypeBadge type={entity.type} />
                <span dir="auto" className="break-anywhere">
                  {entity.display_name}
                </span>
                <span className="font-mono text-xs text-slate-600">{entity.canonical_id}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {response.citations.length > 0 && <CitationList citations={response.citations} />}
    </div>
  );
}

/** The backend's own explanation, kept verbatim but behind progressive disclosure. */
function TechnicalReason({ reason }: { reason: string }) {
  return (
    <details className="rounded-lg border border-line text-sm">
      <summary className="cursor-pointer select-none px-3 py-2 font-medium text-slate-700 hover:bg-slate-50">
        Technical details
      </summary>
      <div className="border-t border-line px-3 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Reason given by the service</p>
        <p className="mt-1 break-anywhere text-slate-800">{reason}</p>
      </div>
    </details>
  );
}

/**
 * Turns "[n]" markers in the backend answer into links to citation n.
 * The answer is rendered as text nodes only; nothing is parsed as HTML.
 */
function AnswerWithMarkers({ answer, citationCount }: { answer: string; citationCount: number }) {
  const parts = answer.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((part, index) => {
        const marker = /^\[(\d+)\]$/.exec(part);
        const number = marker ? Number(marker[1]) : 0;
        if (marker && number >= 1 && number <= citationCount) {
          return (
            <a
              key={index}
              href={`#citation-${number}`}
              className="mx-0.5 rounded bg-blue-50 px-1 font-mono text-xs font-semibold text-blue-700 hover:bg-blue-100"
            >
              [{number}]
            </a>
          );
        }
        return <Fragment key={index}>{part}</Fragment>;
      })}
    </>
  );
}
