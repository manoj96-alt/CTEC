// CDD-079 (WOW-I1) §18: additive only -- the original three kinds are
// unchanged, so every existing call site (loading/empty/error) keeps
// working with zero changes. The four new kinds give later phases a way
// to render a truthful, distinct empty state instead of collapsing every
// not-yet-populated surface into a generic "No data available."
export type EmptyStateKind =
  | "loading"
  | "empty"
  | "error"
  | "not-invoked"
  | "not-authorized"
  | "deferred"
  | "unavailable";

const KIND_EYEBROW: Record<EmptyStateKind, string> = {
  loading: "Loading",
  empty: "No result",
  error: "Error",
  "not-invoked": "Not invoked",
  "not-authorized": "Not authorized",
  deferred: "Deferred",
  unavailable: "Unavailable",
};

export function EmptyState({
  kind,
  title,
  message,
}: {
  kind: EmptyStateKind;
  title: string;
  message?: string;
}) {
  return (
    <section
      className="panel"
      style={{ marginTop: "1rem" }}
      role={kind === "error" ? "alert" : "status"}
      aria-live="polite"
    >
      <span className="eyebrow">{KIND_EYEBROW[kind]}</span>
      <h2 style={{ marginTop: "0.25rem" }}>{title}</h2>
      {message ? <p style={{ color: "var(--muted)" }}>{message}</p> : null}
    </section>
  );
}
