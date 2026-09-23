"use client";

import { useCallback, useEffect, useState } from "react";
import { getServiceStatus } from "@/lib/api";
import type { ServiceStatus as ServiceStatusData } from "@/types/api";

const POLL_INTERVAL_MS = 30_000;

const STATE_STYLES = {
  checking: { dot: "bg-slate-400", label: "Checking services…" },
  ready: { dot: "bg-emerald-400", label: "Services ready" },
  degraded: { dot: "bg-amber-400", label: "Some services degraded" },
  unavailable: { dot: "bg-rose-500", label: "Services unavailable" },
  unknown: { dot: "bg-rose-500", label: "Status unknown" },
} as const;

/** Sidebar readiness indicator driven by /api/status (backend /ready, not /health). */
export function ServiceStatus() {
  const [status, setStatus] = useState<ServiceStatusData | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(async () => {
    const result = await getServiceStatus();
    if (result.ok) {
      setStatus(result.data);
      setFailed(false);
    } else {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    // Initial probe plus a light poll so readiness loss after startup becomes visible.
    const first = setTimeout(refresh, 0);
    const timer = setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [refresh]);

  const state = failed ? "unknown" : status ? status.overall : "checking";
  const style = STATE_STYLES[state];

  return (
    <div className="rounded-lg bg-navy-800/70 text-xs text-slate-200">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex min-h-10 w-full items-center gap-2 px-3 py-2.5 text-left"
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${style.dot}`} aria-hidden />
        <span className="flex-1 font-medium">{style.label}</span>
        <span className="text-slate-400">{open ? "Hide" : "Details"}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-navy-700 px-3 py-2.5">
          {status ? (
            <>
              <ProbeRows name="Query service (FastAPI)" probe={status.fastapi} />
              <ProbeRows name="Ledger service (Django)" probe={status.django} />
            </>
          ) : (
            <p className="text-slate-400">{failed ? "The status endpoint did not respond." : "Waiting for first check."}</p>
          )}
          <button type="button" onClick={refresh} className="font-medium text-blue-300 hover:text-blue-200">
            Re-check now
          </button>
        </div>
      )}
    </div>
  );
}

function ProbeRows({ name, probe }: { name: string; probe: ServiceStatusData["fastapi"] }) {
  return (
    <div>
      <p className="font-medium text-slate-100">
        {name}:{" "}
        <span className={probe.ready ? "text-emerald-300" : "text-amber-300"}>
          {probe.ready ? "ready" : probe.reachable ? "not ready" : "unreachable"}
        </span>
      </p>
      <ul className="mt-0.5 space-y-0.5 text-slate-400">
        {Object.entries(probe.checks).map(([check, value]) => (
          <li key={check}>
            {check}: {value === true || value === "ok" ? "ok" : String(value)}
          </li>
        ))}
      </ul>
    </div>
  );
}
