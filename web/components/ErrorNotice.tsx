import type { ApiError } from "@/lib/api";
import { Button, Notice } from "./ui";

// Plain-language title and guidance per error kind. The raw technical message and
// HTTP status stay available under "Technical details".
const COPY: Record<ApiError["kind"], { title: string; message: string; tone: "warning" | "danger" | "caution" | "neutral" }> = {
  validation: {
    title: "Watheeq couldn't accept this request",
    message: "Please check what you entered and try again.",
    tone: "warning",
  },
  too_large: { title: "Your request is too long", message: "Please shorten it and try again.", tone: "warning" },
  not_found: { title: "Nothing was found", message: "Watheeq has no record matching this.", tone: "neutral" },
  audit_failed_closed: {
    title: "No answer was released",
    message:
      "Watheeq records every question in its audit trail. It couldn't record this one, so it did not release an answer. Please try again shortly.",
    tone: "danger",
  },
  service_unavailable: {
    title: "The required service is temporarily unavailable",
    message: "Please try again in a moment.",
    tone: "caution",
  },
  unreachable: {
    title: "Watheeq couldn't reach the required service",
    message: "The service may be starting up or temporarily offline. Please try again in a moment.",
    tone: "caution",
  },
  timeout: {
    title: "Watheeq took too long to respond",
    message: "The service is busy or slow right now. Please try again.",
    tone: "caution",
  },
  server: { title: "Something went wrong", message: "Watheeq ran into an unexpected problem. Please try again.", tone: "danger" },
  malformed: {
    title: "Watheeq received an unexpected response",
    message: "Nothing is shown rather than risk showing incorrect information. Please try again.",
    tone: "danger",
  },
  network: {
    title: "Connection problem",
    message: "Your browser couldn't reach Watheeq. Check your connection and try again.",
    tone: "caution",
  },
};

const RETRYABLE = new Set<ApiError["kind"]>([
  "audit_failed_closed",
  "service_unavailable",
  "unreachable",
  "timeout",
  "server",
  "malformed",
  "network",
]);

/** Shows a transport/HTTP error in plain language, with an optional "Try again". */
export function ErrorNotice({ error, onRetry, context }: { error: ApiError; onRetry?: () => void; context?: string }) {
  const copy = COPY[error.kind];
  return (
    <Notice
      tone={copy.tone}
      role="alert"
      title={copy.title}
      action={
        onRetry && RETRYABLE.has(error.kind) ? (
          <Button variant="secondary" onClick={onRetry} className="py-1.5">
            Try again
          </Button>
        ) : undefined
      }
    >
      {context && <p className="font-medium">{context}</p>}
      <p>{copy.message}</p>
      <ErrorDetails message={error.message} status={error.status} />
    </Notice>
  );
}

/** Collapsed technical detail for errors: the original message and HTTP status. */
export function ErrorDetails({ message, status }: { message: string; status: number | null }) {
  return (
    <details className="mt-2 text-sm">
      <summary className="cursor-pointer select-none font-medium underline-offset-2 hover:underline">
        Technical details
      </summary>
      <p className="mt-1 break-anywhere">{message}</p>
      {status !== null && <p className="mt-0.5 text-xs">HTTP {status}</p>}
    </details>
  );
}
