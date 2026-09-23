// Browser-side client for the same-origin BFF routes under /api/*.
//
// HTTP/transport failures are normalised here into an ApiError.
// Ask business outcomes (answered, abstained, refused, unsupported, bounded_out,
// unavailable) arrive as HTTP 200 bodies and are returned as data, never as errors.

import {
  ASK_STATUSES,
  type AskRequest,
  type AskResponse,
  type AuditRecord,
  type EntityResolveResponse,
  type LedgerResponse,
  type OwnershipResponse,
  type ServiceStatus,
} from "@/types/api";

export type ApiErrorKind =
  | "validation" // 400 / 422
  | "too_large" // 413
  | "not_found" // 404
  | "audit_failed_closed" // Ask 503: FastAPI refused to answer because audit persistence failed
  | "service_unavailable" // other backend 503
  | "unreachable" // BFF could not reach the backend
  | "timeout" // BFF or backend timed out
  | "server" // other 5xx
  | "malformed" // response did not match the expected contract
  | "network"; // the browser could not reach the web server

export interface ApiError {
  kind: ApiErrorKind;
  status: number | null;
  message: string;
}

export type ApiResult<T> =
  | { ok: true; data: T; requestId: string | null }
  | { ok: false; error: ApiError; requestId: string | null };

type Guard<T> = (value: unknown) => value is T;

async function request<T>(url: string, init: RequestInit, isValid: Guard<T>): Promise<ApiResult<T>> {
  let response: Response;
  try {
    response = await fetch(url, { ...init, cache: "no-store" });
  } catch {
    return {
      ok: false,
      requestId: null,
      error: { kind: "network", status: null, message: "The Watheeq web server could not be reached." },
    };
  }

  const requestId = response.headers.get("x-request-id");
  const body: unknown = await response.json().catch(() => undefined);

  if (!response.ok) {
    return { ok: false, requestId, error: toApiError(response, body) };
  }
  if (!isValid(body)) {
    return {
      ok: false,
      requestId,
      error: { kind: "malformed", status: response.status, message: "The service returned an unexpected response." },
    };
  }
  return { ok: true, data: body, requestId };
}

function toApiError(response: Response, body: unknown): ApiError {
  const status = response.status;
  const detail = detailText(body);
  const bffKind = response.headers.get("x-watheeq-bff-error");

  if (bffKind === "unreachable") return { kind: "unreachable", status, message: detail ?? "Service unreachable." };
  if (bffKind === "timeout" || status === 504) {
    return { kind: "timeout", status, message: detail ?? "The service did not respond in time." };
  }
  if (status === 413) {
    return { kind: "too_large", status, message: "The request is too large. Shorten the input and try again." };
  }
  if (status === 400 || status === 422) {
    return { kind: "validation", status, message: detail ?? "The request was rejected as invalid." };
  }
  if (status === 404) return { kind: "not_found", status, message: detail ?? "Not found." };
  if (status === 503 && detail?.toLowerCase().includes("audit")) {
    return { kind: "audit_failed_closed", status, message: detail };
  }
  if (status === 503) {
    return { kind: "service_unavailable", status, message: detail ?? "A required service is unavailable." };
  }
  return { kind: "server", status, message: detail ?? `Unexpected server error (HTTP ${status}).` };
}

/** Extract a readable message from FastAPI ({detail: str | [{msg}]}) or DRF ({detail: str}) bodies. */
export function detailText(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" ? (item as { msg?: unknown }).msg : null))
      .filter((msg): msg is string => typeof msg === "string");
    if (messages.length) return messages.join("; ");
  }
  return null;
}

// ---------- Minimal shape guards (not full validation; enough to fail safely) ----------

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isResolveResponse: Guard<EntityResolveResponse> = (value): value is EntityResolveResponse =>
  isObject(value) &&
  Array.isArray(value.matches) &&
  value.matches.every(
    (match) =>
      isObject(match) &&
      (match.type === "LegalEntity" || match.type === "NaturalPerson") &&
      typeof match.canonical_id === "string" &&
      typeof match.display_name === "string",
  );

const isOwnershipResponse: Guard<OwnershipResponse> = (value): value is OwnershipResponse =>
  isObject(value) &&
  typeof value.entity_uid === "string" &&
  (value.temporal_mode === "current" || value.temporal_mode === "as_of") &&
  Array.isArray(value.direct_owners) &&
  Array.isArray(value.upstream_paths) &&
  Array.isArray(value.conflicts);

const isAskResponse: Guard<AskResponse> = (value): value is AskResponse =>
  isObject(value) &&
  typeof value.status === "string" &&
  (ASK_STATUSES as readonly string[]).includes(value.status) &&
  typeof value.answer === "string" &&
  Array.isArray(value.citations) &&
  Array.isArray(value.conflicts) &&
  Array.isArray(value.resolved_entities);

const isLedgerResponse: Guard<LedgerResponse> = (value): value is LedgerResponse =>
  isObject(value) &&
  isObject(value.entity) &&
  Array.isArray(value.filings) &&
  Array.isArray(value.ownership_interests);

const isAuditRecord: Guard<AuditRecord> = (value): value is AuditRecord =>
  isObject(value) && typeof value.request_id === "string" && typeof value.outcome === "string";

const isServiceStatus: Guard<ServiceStatus> = (value): value is ServiceStatus =>
  isObject(value) && typeof value.overall === "string" && isObject(value.fastapi) && isObject(value.django);

// ---------- Public API functions ----------

export function resolveEntity(name: string) {
  return request("/api/resolve", jsonPost({ name }), isResolveResponse);
}

/** Current ownership omits asOf; historical ownership passes an exact ISO date. */
export function getOwnership(entityUid: string, asOf: string | null) {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request(`/api/entities/${encodeURIComponent(entityUid)}/ownership${query}`, {}, isOwnershipResponse);
}

export function getLedger(entityUid: string) {
  return request(`/api/ledger/${encodeURIComponent(entityUid)}`, {}, isLedgerResponse);
}

/** Result carries the audit request ID from the X-Request-ID response header. */
export function ask(payload: AskRequest) {
  return request("/api/ask", jsonPost(payload), isAskResponse);
}

export function getAudit(requestId: string) {
  return request(`/api/audit/${encodeURIComponent(requestId)}`, {}, isAuditRecord);
}

export function getServiceStatus() {
  return request("/api/status", {}, isServiceStatus);
}

function jsonPost(payload: unknown): RequestInit {
  return { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) };
}
