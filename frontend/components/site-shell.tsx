"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { SessionControls } from "./session-controls";

// Grouped enterprise information architecture (CDD-033 §8-§9). Exact
// domain order/naming/hrefs mirrored by frontend/tests/gate-x-navigation
// .test.tsx. "Ontology" has no dedicated domain landing among the 29
// authorized Gate X files, so its primary-nav entry links directly to its
// default sub-route (Ontology Explorer).
const primaryNavItems = [
  { label: "Overview", href: "/overview" },
  { label: "Data", href: "/data" },
  { label: "Ontology", href: "/ontology/explorer" },
  { label: "Context", href: "/context" },
  { label: "Quality", href: "/quality" },
  { label: "Intelligence", href: "/intelligence" },
  { label: "Integrations", href: "/integrations" },
  { label: "Governance", href: "/governance" },
  { label: "Administration", href: "/administration" },
];

// Preserved exactly (Artifact Authorization §5 item 1): not part of the
// Gate X domain grouping, kept as a secondary utility group.
const secondaryNavItems = [
  { label: "Home", href: "/" },
  { label: "Architecture", href: "/architecture" },
  { label: "Dataset", href: "/dataset" },
  { label: "Prototype", href: "/prototype" },
  { label: "About", href: "/about" },
];

// CDD-062 §8: a primary nav item is active on an exact match or a
// path-prefix match of its href's first path segment (e.g. "/ontology"
// for "/ontology/explorer") -- so a future sibling route like
// "/ontology/modeling" also correctly activates "Ontology", and
// "/quality/findings/<id>" correctly activates "Quality". Longest
// matching root segment wins, though every current item's root segment
// is already unique, so this is a safety net, not an active
// disambiguation today. Purely presentational -- does not change any
// href, label, or order.
function isNavItemActive(pathname: string, href: string): boolean {
  const rootSegment = "/" + href.split("/").filter(Boolean)[0];
  return pathname === rootSegment || pathname.startsWith(rootSegment + "/");
}

export function SiteShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--line)] bg-white">
        <div className="mx-auto max-w-5xl px-6 py-5 flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Link className="font-bold tracking-tight text-xl" href="/">
              Noetva
            </Link>
            <SessionControls />
          </div>
          <nav
            aria-label="Primary"
            className="flex flex-wrap gap-5 text-sm font-medium"
          >
            {primaryNavItems.map(({ label, href }) => {
              const active = isNavItemActive(pathname ?? "", href);
              return (
                <Link
                  key={label}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  style={active ? { fontWeight: 800 } : undefined}
                  className={active ? "nav-link-active" : undefined}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
          <nav
            aria-label="Secondary"
            className="flex flex-wrap gap-5 text-xs text-[var(--muted)]"
          >
            {secondaryNavItems.map(({ label, href }) => (
              <Link key={label} href={href}>
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-16">
        {children}
      </main>
      <footer className="border-t border-[var(--line)] bg-white px-6 py-5 text-center text-sm text-[var(--muted)]">
        Noetva — Governed Enterprise Understanding
      </footer>
    </div>
  );
}
