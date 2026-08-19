// Displays HUMAN_APPROVAL_REQUIRED as a status only -- no Approve, Reject,
// Override, Execute, Switch-Supplier, or Write-Back control exists here
// or anywhere in this route (CDD-016 §10, §17, PAD-003 §10).
export function HumanAuthorityBanner({ governanceStanding }: { governanceStanding: string | null }) {
  if (governanceStanding !== "HUMAN_APPROVAL_REQUIRED") return null;
  return (
    <section className="panel" aria-label="Human authority" role="status">
      <div className="eyebrow">Human authority</div>
      <p className="standing">
        <strong>Human approval required</strong>
      </p>
      <p>CTEC recommends. A human decides. No action is taken automatically.</p>
    </section>
  );
}
