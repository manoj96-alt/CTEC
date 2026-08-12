import type { Connector } from "@/lib/ontology-studio/contracts";

const MATURITY_COLOR: Record<Connector["maturity"], string> = {
  "Demo Connected": "var(--success)",
  "Skeleton Available": "var(--accent)",
  Roadmap: "var(--muted)",
};

export function ConnectorCatalogPanel({
  connectors,
}: {
  connectors: Connector[];
}) {
  return (
    <section className="panel" style={{ marginTop: "1.5rem" }}>
      <p className="eyebrow">Connector Catalog</p>
      <h2 style={{ marginTop: "0.25rem" }}>Enterprise Sources</h2>
      <div
        style={{
          marginTop: "1rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(15rem, 1fr))",
          gap: "0.75rem",
        }}
      >
        {connectors.map((connector) => (
          <div
            key={connector.connector_id}
            className="panel"
            style={{ margin: 0, fontSize: "0.85rem" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
              }}
            >
              <p style={{ fontWeight: 700 }}>{connector.display_name}</p>
              <span
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  color: MATURITY_COLOR[connector.maturity],
                  border: `1px solid ${MATURITY_COLOR[connector.maturity]}`,
                  borderRadius: "999px",
                  padding: "0.1rem 0.5rem",
                  whiteSpace: "nowrap",
                }}
              >
                {connector.maturity}
              </span>
            </div>
            <p style={{ color: "var(--muted)", marginTop: "0.25rem" }}>
              {connector.source_system_type}
            </p>
            <p style={{ color: "var(--muted)", marginTop: "0.25rem" }}>
              Auth: {connector.authentication_type}
            </p>
            <p style={{ color: "var(--muted)", marginTop: "0.25rem" }}>
              Objects: {connector.supported_object_categories.join(", ")}
            </p>
            <p style={{ color: "var(--muted)", marginTop: "0.25rem" }}>
              Status: {connector.health_status}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
