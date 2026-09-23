import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import type { AnchorHTMLAttributes } from "react";
import { afterEach, vi } from "vitest";

// Render next/link as a plain anchor so tests can assert hrefs without a Next router.
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
// "server-only" throws outside a server bundle; it is irrelevant in unit tests.
vi.mock("server-only", () => ({}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
