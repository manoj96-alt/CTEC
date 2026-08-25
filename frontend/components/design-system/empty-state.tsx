export type EmptyStateKind = "loading" | "empty" | "error";

const KIND_EYEBROW: Record<EmptyStateKind, string> = {
  loading: "Loading",
  empty: "No result",
  error: "Error",
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
