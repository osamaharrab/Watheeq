export const dynamic = "force-dynamic";

// Liveness of the web process only. It intentionally does not probe the backend,
// so the frontend container stays healthy (and can show degraded states) when
// FastAPI or Django are down.
export function GET() {
  return Response.json({ status: "ok", service: "web" });
}
