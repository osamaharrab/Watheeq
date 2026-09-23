import { describe, expect, it, vi } from "vitest";
import { POST as askRoute } from "@/app/api/ask/route";
import { GET as ownershipRoute } from "@/app/api/entities/[entityUid]/ownership/route";

const params = (entityUid: string) => ({ params: Promise.resolve({ entityUid }) });

describe("BFF routes", () => {
  it("omits as_of for current ownership and forwards an exact date for historical", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
    await ownershipRoute(new Request("http://web/api/entities/LE-1/ownership"), params("LE-1"));
    await ownershipRoute(new Request("http://web/api/entities/LE-1/ownership?as_of=2025-09-14"), params("LE-1"));
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/api\/v1\/entities\/LE-1\/ownership$/);
    expect(String(fetchMock.mock.calls[1][0])).toMatch(/\/ownership\?as_of=2025-09-14$/);
  });

  it("rejects a malformed as_of before calling the backend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const response = await ownershipRoute(new Request("http://web/x?as_of=today"), params("LE-1"));
    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("relays X-Request-ID and the business body unchanged", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({ status: "refused", answer: "no" }, { headers: { "x-request-id": "rid-1" } }),
    );
    const response = await askRoute(new Request("http://web/api/ask", { method: "POST", body: '{"question":"q"}' }));
    expect(response.status).toBe(200);
    expect(response.headers.get("x-request-id")).toBe("rid-1");
    expect(await response.json()).toEqual({ status: "refused", answer: "no" });
  });

  it("labels an unreachable backend as a BFF transport error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fetch failed"));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const response = await askRoute(new Request("http://web/api/ask", { method: "POST", body: '{"question":"q"}' }));
    expect(response.status).toBe(502);
    expect(response.headers.get("x-watheeq-bff-error")).toBe("unreachable");
  });
});
