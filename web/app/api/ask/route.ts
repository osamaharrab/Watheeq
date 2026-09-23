import { bffError, proxyToBackend } from "@/lib/backend";
import { MAX_REQUEST_BODY_BYTES } from "@/lib/validation";

export const dynamic = "force-dynamic";

// The local Ollama planner can take well over a minute on CPU, and FastAPI's own
// model timeout is 120s, so the BFF waits longer than that before giving up.
const ASK_TIMEOUT_MS = 200_000;

// POST /api/ask -> FastAPI POST /api/v1/ask (relays the X-Request-ID header)
export async function POST(request: Request) {
  const body = await request.text();
  if (new TextEncoder().encode(body).length > MAX_REQUEST_BODY_BYTES) {
    return bffError(413, "too_large", "Request body is too large");
  }
  return proxyToBackend("fastapi", "/api/v1/ask", { method: "POST", body, timeoutMs: ASK_TIMEOUT_MS });
}
