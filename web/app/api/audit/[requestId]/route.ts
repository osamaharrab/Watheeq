import { bffError, proxyToBackend } from "@/lib/backend";
import { isRequestId } from "@/lib/validation";

export const dynamic = "force-dynamic";

// GET /api/audit/{request_id} -> Django GET /api/v1/audit/{request_id} (read-only).
// Django's POST /internal/audit write endpoint is deliberately never proxied.
export async function GET(_request: Request, { params }: { params: Promise<{ requestId: string }> }) {
  const { requestId } = await params;
  if (!isRequestId(requestId)) return bffError(400, "invalid_input", "Invalid request ID");
  return proxyToBackend("django", `/api/v1/audit/${requestId}`);
}
