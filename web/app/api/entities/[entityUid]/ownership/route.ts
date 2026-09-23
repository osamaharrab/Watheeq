import { bffError, proxyToBackend } from "@/lib/backend";
import { isIsoDate, isSafeId } from "@/lib/validation";

export const dynamic = "force-dynamic";

// GET /api/entities/{uid}/ownership[?as_of=YYYY-MM-DD] -> FastAPI ownership endpoint.
// Current ownership omits as_of entirely; it is never replaced with today's date.
export async function GET(request: Request, { params }: { params: Promise<{ entityUid: string }> }) {
  const { entityUid } = await params;
  if (!isSafeId(entityUid)) return bffError(400, "invalid_input", "Invalid entity identifier");

  const asOf = new URL(request.url).searchParams.get("as_of");
  if (asOf !== null && !isIsoDate(asOf)) {
    return bffError(422, "invalid_input", "as_of must be an ISO date (YYYY-MM-DD)");
  }
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return proxyToBackend("fastapi", `/api/v1/entities/${encodeURIComponent(entityUid)}/ownership${query}`);
}
