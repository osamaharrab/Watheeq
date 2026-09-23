import { EntityWorkspace } from "@/components/workspace/EntityWorkspace";
import { isIsoDate } from "@/lib/validation";

export default async function EntityWorkspacePage({
  params,
  searchParams,
}: {
  params: Promise<{ entityUid: string }>;
  searchParams: Promise<{ as_of?: string | string[] }>;
}) {
  const { entityUid } = await params;
  const { as_of } = await searchParams;
  // Only an exact ISO date selects historical mode; anything else falls back to current.
  const initialAsOf = typeof as_of === "string" && isIsoDate(as_of) ? as_of : null;
  const uid = safeDecode(entityUid);
  return <EntityWorkspace key={`${uid}|${initialAsOf ?? ""}`} entityUid={uid} initialAsOf={initialAsOf} />;
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
