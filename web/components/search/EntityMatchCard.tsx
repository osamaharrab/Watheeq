import Link from "next/link";
import type { EntityMatch } from "@/types/api";
import { EntityTypeBadge } from "../EntityTypeBadge";
import { Badge } from "../ui";

const METADATA_LABELS: Record<string, string> = {
  jurisdiction: "Jurisdiction",
  registration_no: "Registration no.",
  nationality: "Nationality",
};

/** One resolver candidate. The analyst must choose explicitly; nothing is auto-selected. */
export function EntityMatchCard({ match }: { match: EntityMatch }) {
  const metadata = Object.entries(match.metadata ?? {}).filter(
    ([, value]) => value !== null && value !== undefined && value !== "",
  );
  const isLegalEntity = match.type === "LegalEntity";

  return (
    <li className="flex flex-col gap-4 rounded-xl border border-line bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <EntityTypeBadge type={match.type} />
          {match.match_method === "exact" ? (
            <Badge tone="neutral">Exact match</Badge>
          ) : (
            <Badge tone="warning">Possible match (not exact)</Badge>
          )}
        </div>
        {/* Registry names are untrusted text: rendered inert, direction auto for Arabic. */}
        <p dir="auto" className="mt-2 break-anywhere text-lg font-semibold text-slate-900">
          {match.display_name}
        </p>
        <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <div className="flex gap-1.5">
            <dt className="text-slate-600">ID</dt>
            <dd className="font-mono text-sm font-medium text-slate-900">{match.canonical_id}</dd>
          </div>
          {metadata.map(([key, value]) => (
            <div key={key} className="flex min-w-0 gap-1.5">
              <dt className="text-slate-600">{METADATA_LABELS[key] ?? key}</dt>
              <dd className="break-anywhere text-slate-800">{String(value)}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="flex shrink-0 flex-wrap gap-2">
        {isLegalEntity ? (
          <>
            <Link
              href={`/entities/${encodeURIComponent(match.canonical_id)}`}
              className="inline-flex min-h-10 items-center rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
            >
              View ownership
            </Link>
            <Link
              href={`/ask?entity=${encodeURIComponent(match.canonical_id)}`}
              className="inline-flex min-h-10 items-center rounded-lg border border-line px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              Ask about this entity
            </Link>
          </>
        ) : (
          // Natural persons have no ownership workspace in the backend; route to Ask with context.
          <Link
            href={`/ask?entity=${encodeURIComponent(match.canonical_id)}`}
            className="inline-flex min-h-10 items-center rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
          >
            Ask about this person
          </Link>
        )}
      </div>
    </li>
  );
}
