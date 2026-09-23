"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { ServiceStatus } from "./ServiceStatus";

const NAV_ITEMS = [
  { href: "/", label: "Entity Search", isActive: (path: string) => path === "/" },
  { href: "/entities", label: "Ownership", isActive: (path: string) => path.startsWith("/entities") },
  { href: "/ask", label: "Ask Watheeq", isActive: (path: string) => path.startsWith("/ask") },
];

/** Persistent navy sidebar on desktop; compact top bar with a toggle below lg. */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const [menuOpen, setMenuOpen] = useState(false);

  const navigation = (
    <nav aria-label="Primary" className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const active = item.isActive(pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setMenuOpen(false)}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-10 items-center gap-3 rounded-lg px-3 py-2.5 text-[14px] font-medium transition-colors ${
              active ? "bg-navy-700 text-white" : "text-slate-300 hover:bg-navy-800 hover:text-white"
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-blue-400" : "bg-slate-500"}`} aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );

  const brand = (
    <div>
      <p className="text-lg font-bold tracking-[0.18em] text-white">WATHEEQ</p>
      <p className="mt-1 text-xs text-slate-300">Corporate Ownership Intelligence</p>
    </div>
  );

  return (
    <div className="min-h-screen lg:flex">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col bg-navy-900 px-4 py-6 lg:flex">
        <div className="px-2">{brand}</div>
        <div className="mt-8 flex-1">{navigation}</div>
        <ServiceStatus />
      </aside>

      {/* Tablet / mobile top bar */}
      <header className="sticky top-0 z-20 bg-navy-900 px-4 py-3 lg:hidden">
        <div className="flex items-center justify-between gap-3">
          {brand}
          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            className="min-h-10 rounded-md border border-navy-700 px-3 py-1.5 text-sm font-medium text-slate-200"
          >
            {menuOpen ? "Close" : "Menu"}
          </button>
        </div>
        {menuOpen && (
          <div id="mobile-menu" className="mt-3 space-y-3 border-t border-navy-700 pt-3">
            {navigation}
            <ServiceStatus />
          </div>
        )}
      </header>

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        <div className="mx-auto max-w-[1560px]">{children}</div>
      </main>
    </div>
  );
}
