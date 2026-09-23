import "server-only";

// Server-side access to the existing Watheeq services.
// Browser code never sees these URLs; it only calls same-origin /api/* routes.

export type BackendService = "fastapi" | "django";

// Headers the BFF adds when the failure happened between Next.js and the backend,
// so the browser can tell "backend said 503" apart from "backend unreachable".
export const BFF_ERROR_HEADER = "x-watheeq-bff-error";

const DEFAULT_TIMEOUT_MS = 15_000;

export function backendBaseUrl(service: BackendService): string {
  // Docker sets these to http://fastapi:8000 and http://django:8000.
  // The localhost defaults match the host ports for non-Docker development.
  const value =
    service === "fastapi"
      ? process.env.FASTAPI_BASE_URL ?? "http://localhost:8001"
      : process.env.DJANGO_BASE_URL ?? "http://localhost:8000";
  return value.replace(/\/+$/, "");
}

interface ProxyOptions {
  method?: "GET" | "POST";
  body?: string;
  timeoutMs?: number;
}

/**
 * Forward one request to a backend service and relay its status and body unchanged.
 * Backend business outcomes (including 4xx/5xx bodies) pass through untouched;
 * only transport failures are converted into a small, labelled BFF error.
 */
export async function proxyToBackend(
  service: BackendService,
  path: string,
  { method = "GET", body, timeoutMs = DEFAULT_TIMEOUT_MS }: ProxyOptions = {},
): Promise<Response> {
  let upstream: Response;
  try {
    upstream = await fetch(`${backendBaseUrl(service)}${path}`, {
      method,
      body,
      headers: body !== undefined ? { "content-type": "application/json" } : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    const timedOut = error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError");
    // Log the error class only; never log configuration or request bodies.
    console.error(`[bff] ${service} ${method} failed: ${timedOut ? "timeout" : "unreachable"}`);
    return bffError(
      timedOut ? 504 : 502,
      timedOut ? "timeout" : "unreachable",
      timedOut
        ? `The ${serviceLabel(service)} did not respond in time.`
        : `The ${serviceLabel(service)} could not be reached.`,
    );
  }

  const headers = new Headers({
    "content-type": upstream.headers.get("content-type") ?? "application/json",
    "cache-control": "no-store",
  });
  // The Ask audit ID is only available as a response header, so relay it explicitly.
  const requestId = upstream.headers.get("x-request-id");
  if (requestId) headers.set("x-request-id", requestId);

  return new Response(await upstream.text(), { status: upstream.status, headers });
}

export function bffError(status: number, kind: string, detail: string): Response {
  return Response.json(
    { detail },
    { status, headers: { [BFF_ERROR_HEADER]: kind, "cache-control": "no-store" } },
  );
}

function serviceLabel(service: BackendService): string {
  return service === "fastapi" ? "query service" : "ledger service";
}
