import Link from "next/link";
import type { ExecutionSummary } from "@/lib/supplier-risk/contracts";
import { outcomeLabel } from "@/lib/supplier-risk/mappers";
export function AssessmentTable({ items }: { items: ExecutionSummary[] }) {
  if (!items.length)
    return (
      <div className="empty">
        <h2>No assessments yet</h2>
        <p>Start an assessment when supplier-risk evidence requires review.</p>
      </div>
    );
  return (
    <div className="table-wrap">
      <table>
        <caption>Supplier-risk assessment work queue</caption>
        <thead>
          <tr>
            <th>Subject</th>
            <th>Status</th>
            <th>Outcome</th>
            <th>Stage</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.logical_execution_identifier}>
              <th scope="row">
                <Link
                  href={`/supplier-risk/executions/${item.logical_execution_identifier}`}
                >
                  {item.subject_summary}
                </Link>
                <small>{item.logical_execution_identifier}</small>
              </th>
              <td>{item.execution_status}</td>
              <td>{outcomeLabel(item.terminal_classification)}</td>
              <td>{item.current_or_terminal_stage ?? "—"}</td>
              <td>{new Date(item.last_updated_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
