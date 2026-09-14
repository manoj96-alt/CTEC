"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  Compass,
  Database,
  LayoutDashboard,
  Network,
  Plug,
  ScaleIcon,
  Settings,
  ShieldCheck,
  Sparkles,
  Telescope,
} from "lucide-react";
import { SessionControls } from "./session-controls";

// Grouped enterprise information architecture (CDD-033 §8-§9). Exact
// domain order/naming/hrefs mirrored by frontend/tests/gate-x-navigation
// .test.tsx. "Ontology" has no dedicated domain landing among the 29
// authorized Gate X files, so its primary-nav entry links directly to its
// default sub-route (Ontology Explorer).
//
// CDD-079 (WOW-I1) §12: icons are decorative reinforcement only, never a
// replacement for the text label (icon + label always together), and
// never the sole carrier of active/inactive state (aria-current + a
// visible background/underline treatment in globals.css do that).
const primaryNavItems = [
  { label: "Overview", href: "/overview", icon: LayoutDashboard },
  { label: "Data", href: "/data", icon: Database },
  { label: "Ontology", href: "/ontology/explorer", icon: Network },
  { label: "Context", href: "/context", icon: Compass },
  { label: "Quality", href: "/quality", icon: ShieldCheck },
  { label: "Intelligence", href: "/intelligence", icon: Sparkles },
  { label: "Integrations", href: "/integrations", icon: Plug },
  { label: "Governance", href: "/governance", icon: ScaleIcon },
  { label: "Administration", href: "/administration", icon: Settings },
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
    <div className="observatory-shell">
      <header className="observatory-header">
        <div className="observatory-header-inner">
          <div className="observatory-brand-row">
            <Link className="observatory-wordmark" href="/">
              <Telescope
                className="observatory-wordmark-mark"
                size={20}
                aria-hidden="true"
              />
              Noetva
            </Link>
            <SessionControls />
          </div>
          <nav aria-label="Primary" className="observatory-nav">
            {primaryNavItems.map(({ label, href, icon: Icon }) => {
              const active = isNavItemActive(pathname ?? "", href);
              return (
                <Link
                  key={label}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className="observatory-nav-link"
                >
                  <Icon size={16} aria-hidden="true" />
                  {label}
                </Link>
              );
            })}
          </nav>
          <nav aria-label="Secondary" className="observatory-nav-secondary">
            {secondaryNavItems.map(({ label, href }) => (
              <Link key={label} href={href}>
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="observatory-main">{children}</main>
      <footer
        className="observatory-header"
        style={{
          borderTop: "1px solid var(--obs-border)",
          borderBottom: 0,
          textAlign: "center",
          padding: "1.1rem 1.5rem",
          fontSize: "0.85rem",
          color: "var(--obs-text-muted)",
        }}
      >
        Noetva — Governed Enterprise Understanding
      </footer>
    </div>
  );
}
