"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ask, getAudit, resolveEntity, type ApiError } from "@/lib/api";
import { askExamples } from "@/lib/examples";
import { isIsoDate, MAX_QUESTION_CHARS } from "@/lib/validation";
import type { AskRequest, AskResponse, EntityMatch } from "@/types/api";
import { EntityTypeBadge } from "../EntityTypeBadge";
import { ErrorDetails, ErrorNotice } from "../ErrorNotice";
import { PageHeader } from "../PageHeader";
import { Button, ExampleChips, Notice, Panel, Spinner } from "../ui";
import { AskResult } from "./AskResult";
import { AuditPanel, type AuditState } from "./AuditPanel";

type ContextState =
  | { kind: "none" }
  | { kind: "loading"; id: string }
  | { kind: "ok"; entity: EntityMatch }
  | { kind: "unconfirmed"; id: string; error?: ApiError };

type AskState =
  | { kind: "idle" }
  | { kind: "loading"; payload: AskRequest }
  | { kind: "done"; payload: AskRequest; response: AskResponse; requestId: string | null }
  | { kind: "error"; payload: AskRequest; error: ApiError };

export function AskWatheeq({ contextId }: { contextId: string | null }) {
  const [context, setContext] = useState<ContextState>(contextId ? { kind: "loading", id: contextId } : { kind: "none" });
  const [question, setQuestion] = useState("");
  const [asOf, setAsOf] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [askState, setAskState] = useState<AskState>({ kind: "idle" });
  const [audit, setAudit] = useState<AuditState>({ kind: "idle" });
  const [elapsed, setElapsed] = useState(0);
  const askNumber = useRef(0);

  // Confirm the selected context by its canonical ID so the displayed name comes from the backend, not the URL.
  useEffect(() => {
    if (!contextId) return;
    let cancelled = false;
    resolveEntity(contextId).then((result) => {
      if (cancelled) return;
      if (!result.ok) {
        setContext({ kind: "unconfirmed", id: contextId, error: result.error });
        return;
      }
      const exact = result.data.matches.filter(
        (match) => match.match_method === "exact" && match.canonical_id.toLowerCase() === contextId.toLowerCase(),
      );
      setContext(exact.length === 1 ? { kind: "ok", entity: exact[0] } : { kind: "unconfirmed", id: contextId });
    });
    return () => {
      cancelled = true;
    };
  }, [contextId]);

  // Elapsed-time counter while the local model plans the query.
  useEffect(() => {
    if (askState.kind !== "loading") return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [askState.kind]);

  const loadAudit = useCallback(async (requestId: string) => {
    setAudit({ kind: "loading" });
    const result = await getAudit(requestId);
    // An audit lookup failure never removes the answer; it only affects this panel.
    setAudit(result.ok ? { kind: "ok", record: result.data } : { kind: "error", error: result.error });
  }, []);

  const submit = useCallback(
    async (payload: AskRequest) => {
      const current = ++askNumber.current;
      setElapsed(0);
      setAskState({ kind: "loading", payload });
      setAudit({ kind: "idle" });
      const result = await ask(payload);
      if (current !== askNumber.current) return;
      if (!result.ok) {
        setAskState({ kind: "error", payload, error: result.error });
        return;
      }
      setAskState({ kind: "done", payload, response: result.data, requestId: result.requestId });
      if (result.requestId) {
        loadAudit(result.requestId);
      } else {
        setAudit({ kind: "no_request_id" });
      }
    },
    [loadAudit],
  );

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setFormError("Enter an ownership question.");
      return;
    }
    if (question.length > MAX_QUESTION_CHARS) {
      setFormError(`Questions must be ${MAX_QUESTION_CHARS} characters or fewer.`);
      return;
    }
    if (asOf && !isIsoDate(asOf)) {
      setFormError("The as-of date must be a valid date (YYYY-MM-DD).");
      return;
    }
    setFormError(null);
    // The backend contract is {question, as_of?}; as_of is omitted entirely for current ownership.
    submit(asOf ? { question, as_of: asOf } : { question });
  }

  const examples = askExamples(
    context.kind === "ok" ? { id: context.entity.canonical_id, type: context.entity.type } : null,
  );

  // Fills the form only; the analyst still reviews and submits the question.
  function pickExample(index: number) {
    const example = examples[index];
    setQuestion(example.question);
    setAsOf(example.asOf ?? "");
    setFormError(null);
    document.getElementById("question")?.focus();
  }

  const loading = askState.kind === "loading";
  const response = askState.kind === "done" ? askState.response : null;
  const requestId = askState.kind === "done" ? askState.requestId : null;

  return (
    <>
      <PageHeader
        title="Ask Watheeq"
        subtitle="Ask who owns a company, now or on a past date. Every answer links back to its evidence."
        actions={<ContextChip context={context} />}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px] 2xl:grid-cols-[minmax(0,1fr)_460px]">
        <div className="min-w-0 space-y-6">
          <Panel>
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <ContextBanner context={context} />
              <div>
                <div className="flex items-baseline justify-between gap-2">
                  <label htmlFor="question" className="text-base font-semibold text-slate-900">
                    Your ownership question
                  </label>
                  <span className="text-xs text-slate-500">
                    {question.length}/{MAX_QUESTION_CHARS}
                  </span>
                </div>
                <textarea
                  id="question"
                  dir="auto"
                  rows={3}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Type a question, e.g. Who currently owns LE-005?"
                  className="mt-2 w-full resize-y rounded-lg border border-slate-300 bg-slate-50 px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <ExampleChips
                examples={examples.map((example) => ({
                  label: example.question,
                  hint: example.asOf ? `sets date ${example.asOf}` : undefined,
                }))}
                onPick={pickExample}
              />
              <div className="flex flex-col gap-4 border-t border-line pt-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <label htmlFor="ask-as-of" className="text-sm font-medium text-slate-700">
                    Date <span className="font-normal text-slate-600">(optional)</span>
                  </label>
                  <div className="mt-1 flex items-center gap-2">
                    <input
                      id="ask-as-of"
                      type="date"
                      value={asOf}
                      onChange={(event) => setAsOf(event.target.value)}
                      className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    />
                    {asOf && (
                      <button
                        type="button"
                        onClick={() => setAsOf("")}
                        className="min-h-10 rounded-md px-2 text-sm font-medium text-blue-700 hover:bg-blue-50 hover:underline"
                      >
                        Clear date
                      </button>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    {asOf
                      ? "Watheeq will answer for ownership on this exact date."
                      : "Leave empty for current ownership. For a past date, choose it here rather than typing it."}
                  </p>
                </div>
                <Button type="submit" disabled={loading} className="sm:w-40">
                  {loading ? "Asking…" : "Ask Watheeq"}
                </Button>
              </div>
              {formError && (
                <p role="alert" className="text-sm text-rose-700">
                  {formError}
                </p>
              )}
            </form>
          </Panel>

          <Panel>
            {askState.kind === "idle" && (
              <p className="text-sm text-slate-600">
                Your result will appear here. If Watheeq can&apos;t verify an answer from its records, it says so
                instead of guessing.
              </p>
            )}
            {askState.kind === "loading" && (
              <div className="space-y-2">
                <Spinner label={`Checking Watheeq's records… ${elapsed}s`} />
                <p className="text-sm text-slate-600">
                  Watheeq verifies every answer against its records. This can take a minute or two.
                </p>
              </div>
            )}
            {askState.kind === "error" && (
              <ErrorNotice error={askState.error} context="Your question wasn't answered." onRetry={() => submit(askState.payload)} />
            )}
            {askState.kind === "done" && (
              <AskResult
                response={askState.response}
                asOf={askState.payload.as_of ?? null}
                question={askState.payload.question}
                onRetry={() => submit(askState.payload)}
              />
            )}
          </Panel>
        </div>

        <Panel
          title="Evidence & audit trail"
          description="See where this result came from and review its audit record."
          className="h-fit xl:sticky xl:top-8"
        >
          <AuditPanel
            requestId={requestId}
            response={response}
            audit={audit}
            onRetry={() => requestId && loadAudit(requestId)}
          />
        </Panel>
      </div>
    </>
  );
}

function ContextChip({ context }: { context: ContextState }) {
  if (context.kind !== "ok") return null;
  return (
    <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-800 ring-1 ring-blue-100">
      Selected: <span className="font-mono">{context.entity.canonical_id}</span>
    </span>
  );
}

/** Shows the selected company or person. Examples below the question use its ID. */
function ContextBanner({ context }: { context: ContextState }) {
  if (context.kind === "none") return null;
  if (context.kind === "loading") return <Spinner label={`Checking Watheeq's records for ${context.id}…`} />;
  if (context.kind === "unconfirmed") {
    return (
      <Notice tone="warning" title={`Watheeq couldn't confirm the selected entity “${context.id}”`}>
        You can still ask a question, or{" "}
        <Link href="/" className="font-semibold underline">
          find the entity in Entity Search
        </Link>
        .
        {context.error && <ErrorDetails message={context.error.message} status={context.error.status} />}
      </Notice>
    );
  }

  const { entity } = context;
  const id = entity.canonical_id;
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-blue-100 bg-blue-50/60 p-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">Selected</span>
          <EntityTypeBadge type={entity.type} />
        </div>
        <p dir="auto" className="mt-1 break-anywhere text-base font-semibold text-slate-900">
          {entity.display_name} <span className="font-mono text-sm font-normal text-slate-600">{id}</span>
        </p>
        <p className="mt-1 text-sm text-slate-600">
          {entity.type === "NaturalPerson"
            ? "Ask which companies this person holds interests in. Include the ID in your question."
            : "Include the ID in your question so Watheeq knows exactly which entity you mean."}
        </p>
      </div>
      {entity.type === "LegalEntity" && (
        <Link
          href={`/entities/${encodeURIComponent(id)}`}
          className="inline-flex min-h-10 items-center rounded-lg border border-line bg-white px-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
        >
          View ownership
        </Link>
      )}
    </div>
  );
}
