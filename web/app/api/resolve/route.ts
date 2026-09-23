import { bffError, proxyToBackend } from "@/lib/backend";
import { MAX_REQUEST_BODY_BYTES } from "@/lib/validation";

export const dynamic = "force-dynamic";

// POST /api/resolve -> FastAPI POST /api/v1/entities/resolve
export async function POST(request: Request) {
  const body = await request.text();
  if (new TextEncoder().encode(body).length > MAX_REQUEST_BODY_BYTES) {
    return bffError(413, "too_large", "Request body is too large");
  }
  // The body is forwarded as-is so FastAPI's strict validation stays authoritative.
  return proxyToBackend("fastapi", "/api/v1/entities/resolve", { method: "POST", body });
}
