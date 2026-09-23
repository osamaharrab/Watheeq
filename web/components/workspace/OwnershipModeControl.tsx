"use client";

import { useState, type FormEvent } from "react";
import { isIsoDate } from "@/lib/validation";

/**
 * Current vs Historical switch.
 * Current sends no date at all (backend: valid_to IS NULL).
 * Historical sends one exact ISO date (backend: inclusive valid_from/valid_to).
 */
export function OwnershipModeControl({
  asOf,
  onChange,
  disabled,
}: {
  asOf: string | null;
  onChange: (asOf: string | null) => void;
  disabled?: boolean;
}) {
  const [historical, setHistorical] = useState(asOf !== null);
  const [draftDate, setDraftDate] = useState(asOf ?? "");
  const [error, setError] = useState<string | null>(null);

  function selectCurrent() {
    setHistorical(false);
    setError(null);
    if (asOf !== null) onChange(null);
  }

  function applyDate(event: FormEvent) {
    event.preventDefault();
    if (!isIsoDate(draftDate)) {
      setError("Choose a valid date (YYYY-MM-DD).");
      return;
    }
    setError(null);
    onChange(draftDate);
  }

  return (
    <div className="space-y-3">
      <div role="group" aria-label="Ownership view" className="grid gap-3 sm:grid-cols-2 lg:max-w-3xl">
        <ModeOption
          active={!historical}
          title="Current ownership"
          description="View the latest recorded ownership."
          onClick={selectCurrent}
          disabled={disabled}
        />
        <ModeOption
          active={historical}
          title="Historical ownership"
          description="View ownership as it was recorded on a specific date."
          onClick={() => setHistorical(true)}
          disabled={disabled}
        />
      </div>

      {historical && (
        <form
          onSubmit={applyDate}
          className="flex flex-wrap items-end gap-3 rounded-lg border border-blue-200 bg-blue-50/60 p-4 lg:max-w-3xl"
        >
          <div>
            <label htmlFor="as-of-date" className="block text-sm font-semibold text-slate-800">
              Show ownership on
            </label>
            <input
              id="as-of-date"
              type="date"
              value={draftDate}
              onChange={(event) => setDraftDate(event.target.value)}
              className="mt-1 min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <button
            type="submit"
            disabled={disabled}
            className="min-h-10 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:bg-blue-300"
          >
            Show ownership
          </button>
          {error && (
            <p role="alert" className="w-full text-sm text-rose-700">
              {error}
            </p>
          )}
          {!error && (
            <p className="w-full text-sm text-slate-600">
              {asOf === null
                ? "Choose a date to see who held ownership on that exact day."
                : "Records that start or end on the chosen date are included."}
            </p>
          )}
        </form>
      )}
    </div>
  );
}

/** One selectable view. Selection is shown by a filled marker and label, not by colour alone. */
function ModeOption({
  active,
  title,
  description,
  onClick,
  disabled,
}: {
  active: boolean;
  title: string;
  description: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      disabled={disabled}
      className={`flex min-h-10 items-start gap-3 rounded-lg border bg-white p-4 text-left transition-colors ${
        active ? "border-blue-500 ring-1 ring-blue-500" : "border-line hover:border-slate-400"
      }`}
    >
      <span
        aria-hidden
        className={`mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 ${
          active ? "border-blue-700" : "border-slate-400"
        }`}
      >
        {active && <span className="h-2 w-2 rounded-full bg-blue-700" />}
      </span>
      <span>
        <span className="block text-base font-semibold text-slate-900">
          {title}
          {active && <span className="sr-only"> (selected)</span>}
        </span>
        <span className="mt-0.5 block text-sm text-slate-600">{description}</span>
      </span>
    </button>
  );
}
