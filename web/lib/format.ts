// Display helpers. They format values; they never change or "correct" facts.

/** 10,000 bps = 100%. Values outside 0–10,000 are shown as returned. */
export function bpsToPercent(bps: number): string {
  return `${(bps / 100).toFixed(2)}%`;
}

export function formatBps(bps: number): string {
  return `${bps.toLocaleString("en-US")} bps`;
}

/** Validity window, keeping the backend's inclusive end-date semantics visible. */
export function formatValidity(validFrom: string, validTo: string | null): string {
  return validTo ? `${validFrom} → ${validTo} (inclusive)` : `${validFrom} → open (no end date)`;
}

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "medium", timeZone: "UTC" }) + " UTC";
}

export function entityTypeLabel(type: string): string {
  if (type === "LegalEntity") return "Legal entity";
  if (type === "NaturalPerson") return "Natural person";
  return type;
}

/** Read a string-ish field from loosely typed backend dicts without inventing values. */
export function textField(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (value === null || value === undefined || value === "") return null;
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean" ? String(value) : null;
}
