import Link from "next/link";
import type { Attempt } from "@/lib/supplier-risk/contracts";
export function AttemptHistory({
  logicalId,
  attempts,
}: {
  logicalId: string;
  attempts: Attempt[];
}) {
  return (
    <section className="panel">
      <h2>Attempt history</h2>
      <ul className="record-list">
        {attempts.map((attempt, index) => (
          <li key={attempt.execution_identifier}>
            <Link
              href={`/supplier-risk/executions/${logicalId}/attempts/${attempt.execution_identifier}`}
            >
              Attempt {index + 1}
            </Link>
            <span>{attempt.state}</span>
            <small>{new Date(attempt.admitted_at).toLocaleString()}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}
