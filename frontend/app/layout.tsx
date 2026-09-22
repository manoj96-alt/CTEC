import type { Metadata } from "next";
import type { ReactNode } from "react";
import { IBM_Plex_Mono, Manrope, Sora } from "next/font/google";
import { SiteShell } from "@/components/site-shell";
import "./globals.css";

// CDD-079 (WOW-I1): the governed typography foundation, sourced from
// noetva.ai's real typeface choices (CDD-078 §3) -- Instrument Serif is
// deliberately excluded (marketing-only editorial accent, CDD-079 §4/§7).
// Self-hosted via next/font/google: no external runtime font request, no
// added render-blocking network call (performance contract, CDD-079 §21).
// Exposed as CSS variables only -- `body`'s existing `font-family: Arial`
// rule in globals.css is untouched; only the new Observatory shell and
// primitives opt in via these variables.
const sora = Sora({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-sora",
  display: "swap",
});
const manrope = Manrope({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-manrope",
  display: "swap",
});
const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Noetva", template: "%s · Noetva" },
  description: "Ontology-driven decision intelligence",
};
export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${sora.variable} ${manrope.variable} ${ibmPlexMono.variable}`}
    >
      <body>
        <SiteShell>{children}</SiteShell>
      </body>
    </html>
  );
}
