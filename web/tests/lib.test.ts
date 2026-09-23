import { describe, expect, it } from "vitest";
import { bpsToPercent } from "@/lib/format";
import { summarizeReadiness } from "@/lib/serviceStatus";
import { isIsoDate } from "@/lib/validation";

const probe = (reachable: boolean, ready: boolean) => ({ reachable, ready, httpStatus: null, checks: {} });

describe("helpers", () => {
  it("converts bps without normalising totals", () => {
    expect(bpsToPercent(10000)).toBe("100.00%");
    expect(bpsToPercent(10500)).toBe("105.00%");
    expect(bpsToPercent(1)).toBe("0.01%");
  });

  it("validates exact ISO dates", () => {
    expect(isIsoDate("2025-09-14")).toBe(true);
    expect(isIsoDate("2025-02-30")).toBe(false);
    expect(isIsoDate("14/09/2025")).toBe(false);
  });

  it("summarises readiness into ready / degraded / unavailable", () => {
    expect(summarizeReadiness(probe(true, true), probe(true, true))).toBe("ready");
    expect(summarizeReadiness(probe(true, false), probe(true, true))).toBe("degraded");
    expect(summarizeReadiness(probe(false, false), probe(true, true))).toBe("unavailable");
  });
});
