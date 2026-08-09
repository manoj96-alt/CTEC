import { outcomeLabel } from "@/lib/supplier-risk/mappers";
import type { TerminalClassification } from "@/lib/supplier-risk/contracts";
export function StatusSummary({
  execution,
  outcome,
  stage,
}: {
  execution: string;
  outcome: TerminalClassification | null;
  stage?: string | null;
}) {
  return (
    <dl className="status-grid" aria-label="Assessment status">
      <div>
        <dt>Execution</dt>
        <dd>{execution}</dd>
      </div>
      <div>
        <dt>Business outcome</dt>
        <dd>{outcomeLabel(outcome)}</dd>
      </div>
      <div>
        <dt>Current stage</dt>
        <dd>{stage ?? "Not started"}</dd>
      </div>
    </dl>
  );
}
