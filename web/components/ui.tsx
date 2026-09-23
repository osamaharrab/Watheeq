// Small shared presentation primitives. Deliberately few, plain, and prop-light.

import type { ReactNode } from "react";

export function Panel({
  title,
  description,
  actions,
  children,
  className = "",
  id,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} className={`rounded-xl border border-line bg-white p-5 shadow-sm sm:p-7 ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-lg font-semibold text-slate-900">{title}</h2>}
            {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "caution";

const BADGE_TONES: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  info: "bg-blue-50 text-blue-700 ring-blue-100",
  success: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  warning: "bg-amber-50 text-amber-800 ring-amber-200",
  danger: "bg-rose-50 text-rose-700 ring-rose-100",
  caution: "bg-orange-50 text-orange-800 ring-orange-200",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${BADGE_TONES[tone]}`}
    >
      {children}
    </span>
  );
}

const NOTICE_TONES: Record<Tone, string> = {
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
  info: "border-blue-200 bg-blue-50 text-blue-900",
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  danger: "border-rose-200 bg-rose-50 text-rose-900",
  caution: "border-orange-200 bg-orange-50 text-orange-900",
};

/** A labelled state message (empty, warning, error, notice). Not one generic red box. */
export function Notice({
  tone = "neutral",
  title,
  children,
  action,
  role,
}: {
  tone?: Tone;
  title: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  role?: "alert" | "status";
}) {
  return (
    <div role={role} className={`rounded-lg border px-4 py-3.5 text-sm ${NOTICE_TONES[tone]}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold">{title}</p>
          {children && <div className="mt-1 break-anywhere">{children}</div>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-sm text-slate-600">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function SkeletonRows({ rows = 3, label = "Checking Watheeq's records…" }: { rows?: number; label?: string }) {
  return (
    <div className="space-y-3">
      <p role="status" className="text-sm text-slate-600">
        {label}
      </p>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="h-14 animate-pulse rounded-lg bg-slate-100" aria-hidden />
      ))}
    </div>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  const styles = {
    primary: "bg-blue-700 text-white hover:bg-blue-800 disabled:bg-blue-300",
    secondary: "border border-line bg-white text-slate-800 hover:bg-slate-50 disabled:text-slate-400",
    ghost: "text-blue-700 hover:bg-blue-50 disabled:text-slate-400",
  }[variant];
  return (
    <button
      type="button"
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    />
  );
}

/** Definition list row for label/value pairs. Values render as inert text. */
export function Field({ label, children, mono = false }: { label: string; children: ReactNode; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-600">{label}</dt>
      <dd className={`mt-0.5 break-anywhere text-sm text-slate-900 ${mono ? "font-mono text-[13px]" : ""}`}>
        {children}
      </dd>
    </div>
  );
}

/**
 * "Try an example" chips. Clicking one only fills a form field; it never submits.
 * Real <button>s, so they are reachable and operable by keyboard.
 */
export function ExampleChips({
  examples,
  onPick,
  label = "Try an example",
}: {
  examples: { label: string; hint?: string }[];
  onPick: (index: number) => void;
  label?: string;
}) {
  return (
    <div role="group" aria-label={label}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">{label}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {examples.map((example, index) => (
          <button
            key={example.label}
            type="button"
            onClick={() => onPick(index)}
            title={example.hint}
            className="min-h-10 rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-left text-sm text-slate-800 transition-colors hover:border-blue-400 hover:bg-blue-50 hover:text-blue-800"
          >
            {example.label}
            {example.hint && <span className="ml-1.5 text-xs text-slate-600">· {example.hint}</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
