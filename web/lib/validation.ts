// Small input checks shared by BFF routes and forms.
// These only reject obviously malformed input early; the backend remains the authority.

// Mirrors FastAPI limits in app/schemas.py and app/config.py.
export const MAX_ENTITY_NAME_CHARS = 300;
export const MAX_QUESTION_CHARS = 2000;
export const MAX_REQUEST_BODY_BYTES = 8192;

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
// Canonical IDs are opaque; only bound their size and forbid path separators.
const SAFE_ID = /^[^/\\?#\s]{1,64}$/;

export function isIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(value);
}

export function isRequestId(value: string): boolean {
  return UUID.test(value);
}

export function isSafeId(value: string): boolean {
  return SAFE_ID.test(value);
}
