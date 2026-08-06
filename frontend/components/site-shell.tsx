import Link from "next/link";
import type { ReactNode } from "react";

const links = ["Home", "Architecture", "Dataset", "Prototype", "About"];

export function SiteShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--line)] bg-white">
        <div className="mx-auto max-w-5xl px-6 py-5 flex flex-wrap items-center justify-between gap-4">
          <Link className="font-bold tracking-tight text-xl" href="/">
            CTEC
          </Link>
          <nav
            aria-label="Primary"
            className="flex flex-wrap gap-5 text-sm text-[var(--muted)]"
          >
            {links.map((label) => (
              <Link
                key={label}
                href={label === "Home" ? "/" : `/${label.toLowerCase()}`}
              >
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
        CTEC · Enterprise Cognitive Operating Model prototype
      </footer>
    </div>
  );
}
