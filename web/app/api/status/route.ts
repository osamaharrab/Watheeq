import "server-only";
import { backendBaseUrl, type BackendService } from "@/lib/backend";
import { readinessChecks, summarizeReadiness } from "@/lib/serviceStatus";
import type { ServiceProbe, ServiceStatus } from "@/types/api";

export const dynamic = "force-dynamic";

const PROBE_TIMEOUT_MS = 5_000;

// GET /api/status -> aggregated FastAPI /ready + Django /ready.
// Uses readiness (dependencies), not /health (process liveness only).
export async function GET() {
  const [fastapi, django] = await Promise.all([probe("fastapi"), probe("django")]);
  const status: ServiceStatus = {
    overall: summarizeReadiness(fastapi, django),
    fastapi,
    django,
    checkedAt: new Date().toISOString(),
  };
  return Response.json(status, { headers: { "cache-control": "no-store" } });
}

async function probe(service: BackendService): Promise<ServiceProbe> {
  try {
    const response = await fetch(`${backendBaseUrl(service)}/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
    });
    const body = await response.json().catch(() => null);
    return { reachable: true, ready: response.ok, httpStatus: response.status, checks: readinessChecks(body) };
  } catch {
    return { reachable: false, ready: false, httpStatus: null, checks: {} };
  }
}
