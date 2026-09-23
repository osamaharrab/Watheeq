"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { resolveEntity, type ApiError } from "@/lib/api";
import { SEARCH_EXAMPLES } from "@/lib/examples";
import { MAX_ENTITY_NAME_CHARS } from "@/lib/validation";
import type { EntityMatch } from "@/types/api";
import { ErrorNotice } from "../ErrorNotice";
import { Button, ExampleChips, Notice, SkeletonRows } from "../ui";
import { SearchResults } from "./SearchResults";

type SearchState =
  | { kind: "idle" }
  | { kind: "loading"; query: string }
  | { kind: "done"; query: string; matches: EntityMatch[] }
  | { kind: "error"; query: string; error: ApiError };

export function EntitySearch({ initialQuery = "" }: { initialQuery?: string }) {
  const [input, setInput] = useState(initialQuery);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [state, setState] = useState<SearchState>({ kind: "idle" });
  const latestQuery = useRef<string | null>(null);

  const runSearch = useCallback(async (query: string) => {
    latestQuery.current = query;
    setState({ kind: "loading", query });
    const result = await resolveEntity(query);
    // Ignore responses from searches the analyst has already replaced.
    if (latestQuery.current !== query) return;
    setState(result.ok ? { kind: "done", query, matches: result.data.matches } : { kind: "error", query, error: result.error });
  }, []);

  // Re-run the search from the URL (?q=) so reloads and shared links stay meaningful.
  useEffect(() => {
    const query = initialQuery.trim();
    if (query && query.length <= MAX_ENTITY_NAME_CHARS) {
      const timer = setTimeout(() => runSearch(query), 0);
      return () => clearTimeout(timer);
    }
  }, [initialQuery, runSearch]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const query = input.trim();
    if (!query) {
      setValidationError("Enter a company name, person name or canonical ID.");
      return;
    }
    if (query.length > MAX_ENTITY_NAME_CHARS) {
      setValidationError(`Search text must be ${MAX_ENTITY_NAME_CHARS} characters or fewer.`);
      return;
    }
    setValidationError(null);
    window.history.replaceState(null, "", `/?q=${encodeURIComponent(query)}`);
    runSearch(query);
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} noValidate className="rounded-xl border border-line bg-white p-5 shadow-sm sm:p-6">
        <label htmlFor="entity-query" className="text-base font-semibold text-slate-900">
          Company or person
        </label>
        <p className="mt-0.5 text-sm text-slate-600">Enter a company name, a person&apos;s name, or an entity ID.</p>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <input
            id="entity-query"
            type="search"
            dir="auto"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="e.g. Aqaba Logistics Park Company or LE-005"
            aria-invalid={validationError ? true : undefined}
            aria-describedby={validationError ? "entity-query-error" : undefined}
            className="min-h-11 min-w-0 flex-1 rounded-lg border border-slate-300 bg-slate-50 px-4 py-2.5 text-base text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          <Button type="submit" disabled={state.kind === "loading"} className="min-h-11 sm:w-36">
            {state.kind === "loading" ? "Searching…" : "Search"}
          </Button>
        </div>
        {validationError && (
          <p id="entity-query-error" role="alert" className="mt-2 text-sm text-rose-700">
            {validationError}
          </p>
        )}
        <div className="mt-5">
          {/* Examples only fill the field; the analyst still presses Search. */}
          <ExampleChips
            examples={SEARCH_EXAMPLES.map((label) => ({ label }))}
            onPick={(index) => {
              setInput(SEARCH_EXAMPLES[index]);
              setValidationError(null);
              document.getElementById("entity-query")?.focus();
            }}
          />
        </div>
      </form>

      {state.kind === "idle" && (
        <Notice tone="neutral" title="How search works">
          Watheeq lists every company or person that matches, clearly labelled. If several share a name, you choose the
          right one. Companies open their ownership page; people open Ask Watheeq.
        </Notice>
      )}
      {state.kind === "loading" && (
        <div className="space-y-3">
          <SkeletonRows rows={3} label={`Checking Watheeq's records for “${state.query}”…`} />
        </div>
      )}
      {state.kind === "error" && (
        <ErrorNotice error={state.error} context="Your search couldn't be completed." onRetry={() => runSearch(state.query)} />
      )}
      {state.kind === "done" && <SearchResults query={state.query} matches={state.matches} />}
    </div>
  );
}
