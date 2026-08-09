import type { Stage } from "@/lib/supplier-risk/contracts";
export function StageTimeline({ stages }: { stages: Stage[] }) {
  return (
    <ol className="timeline" aria-label="Capability stage progress">
      {stages.map((stage) => (
        <li key={stage.stage_identifier}>
          <span aria-hidden="true" className="stage-dot" />
          <div>
            <strong>{stage.stage_name}</strong>
            <p>
              {stage.status}
              {stage.safe_failure_code ? ` · ${stage.safe_failure_code}` : ""}
            </p>
            <small>
              {stage.completed_at
                ? `Completed ${new Date(stage.completed_at).toLocaleString()}`
                : "In progress"}
            </small>
          </div>
        </li>
      ))}
    </ol>
  );
}
