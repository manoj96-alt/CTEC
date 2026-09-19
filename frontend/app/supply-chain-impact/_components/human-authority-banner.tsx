// Displays HUMAN_APPROVAL_REQUIRED as a status only -- no Approve, Reject,
// Override, Execute, Switch-Supplier, or Write-Back control exists here
// or anywhere in this route (CDD-016 §10, §17, PAD-003 §10). WOW-I4-B1
// (CDD-085 §7.4/§8): rendered directly beneath RecommendationPanel inside
// the shared `.obs-intelligence-surface` "Governed Decision" block in
// page.tsx -- recommendation and human authority are one visual unit,
// never separated, this statement never smaller or less prominent than
// the recommendation above it.
export function HumanAuthorityBanner({
  governanceStanding,
}: {
  governanceStanding: string | null;
}) {
  if (governanceStanding !== "HUMAN_APPROVAL_REQUIRED") return null;
  return (
    <div
      className="obs-sci-decision-block obs-sci-authority"
      aria-label="Human authority"
      role="status"
    >
      <div className="obs-eu-eyebrow">Human authority</div>
      <p className="standing">
        <strong>Human approval required</strong>
      </p>
      <p>
        Noetva recommends. A human decides. No action is taken automatically.
      </p>
    </div>
  );
}
