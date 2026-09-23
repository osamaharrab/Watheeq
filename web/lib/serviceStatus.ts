import type { OverallServiceState, ServiceProbe } from "@/types/api";

/**
 * Combine the two backend readiness probes into one sidebar state.
 * - ready:       both services report /ready success.
 * - unavailable: the query service cannot be reached at all.
 * - degraded:    anything in between (e.g. FastAPI alive but Ollama or Neo4j not ready).
 */
export function summarizeReadiness(fastapi: ServiceProbe, django: ServiceProbe): OverallServiceState {
  if (fastapi.ready && django.ready) return "ready";
  if (!fastapi.reachable) return "unavailable";
  return "degraded";
}

/** Flatten a backend readiness body into name -> state without inventing checks. */
export function readinessChecks(body: unknown): Record<string, boolean | string> {
  if (!body || typeof body !== "object") return {};
  const record = body as Record<string, unknown>;
  // FastAPI reports { checks: { django: true, ... } }; Django reports { dependencies: { postgres: "ok" } }.
  const source = (record.checks ?? record.dependencies) as unknown;
  if (!source || typeof source !== "object") return {};
  const checks: Record<string, boolean | string> = {};
  for (const [name, value] of Object.entries(source as Record<string, unknown>)) {
    if (typeof value === "boolean" || typeof value === "string") checks[name] = value;
  }
  return checks;
}
