import { bffError, proxyToBackend } from "@/lib/backend";
import { isSafeId } from "@/lib/validation";

export const dynamic = "force-dynamic";

// GET /api/ledger/{uid} -> Django GET /api/v1/ledger/entities/{uid} (authoritative ledger + provenance)
export async function GET(_request: Request, { params }: { params: Promise<{ entityUid: string }> }) {
  const { entityUid } = await params;
  if (!isSafeId(entityUid)) return bffError(400, "invalid_input", "Invalid entity identifier");
  return proxyToBackend("django", `/api/v1/ledger/entities/${encodeURIComponent(entityUid)}`);
}
