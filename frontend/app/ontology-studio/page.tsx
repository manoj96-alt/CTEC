import { redirect } from "next/navigation";

// CDD-083 §3: the bare /ontology-studio index has no real inbound link
// anywhere in the app (independently reverified from CDD-081's own
// correction) and rendered the exact same <StudioClient /> as the
// canonically-linked /ontology/explorer -- a competing, unreachable
// duplicate of the real page, not a distinct experience. Canonicalized
// here rather than deleted, so frontend/tests/gate-x-runtime-
// architecture.test.tsx's existsSync check on this exact path (a
// frozen legacy-deep-link-preservation assertion) continues to pass.
export default function Page() {
  redirect("/ontology/explorer");
}
