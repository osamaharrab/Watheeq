import type { EntityMatch } from "@/types/api";
import { Notice } from "../ui";
import { EntityMatchCard } from "./EntityMatchCard";

/** Renders every candidate in backend order and explains any ambiguity. */
export function SearchResults({ query, matches }: { query: string; matches: EntityMatch[] }) {
  if (matches.length === 0) {
    return (
      <Notice tone="neutral" title="No matching company or person was found" role="status">
        Nothing matched “<span dir="auto">{query}</span>”. Check the spelling, or search by an entity or person ID.
      </Notice>
    );
  }

  const exactMatches = matches.filter((match) => match.match_method === "exact");
  const onlyApproximate = exactMatches.length === 0;
  const types = new Set(matches.map((match) => match.type));

  return (
    <section aria-labelledby="results-heading" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="results-heading" className="text-xl font-semibold text-slate-900">
            Matches
          </h2>
          <p className="text-sm text-slate-600">
            Choose the company or person you mean. Watheeq never picks one for you.
          </p>
        </div>
        <p className="text-sm text-slate-600">
          {matches.length} {matches.length === 1 ? "match" : "matches"}
        </p>
      </div>

      {onlyApproximate && (
        <Notice tone="warning" title="No exact match — these are possible matches" role="status">
          They have similar names to “<span dir="auto">{query}</span>” but may be unrelated. Check the ID and details
          before continuing.
        </Notice>
      )}
      {!onlyApproximate && exactMatches.length > 1 && (
        <Notice tone="caution" title="More than one match — please choose" role="status">
          {exactMatches.length} records match this name exactly
          {types.size > 1 ? ", including both companies and people" : ""}. Watheeq won&apos;t choose for you — compare
          the type, ID and details below.
        </Notice>
      )}

      <ul className="space-y-3">
        {matches.map((match) => (
          <EntityMatchCard key={`${match.type}:${match.canonical_id}`} match={match} />
        ))}
      </ul>
    </section>
  );
}
