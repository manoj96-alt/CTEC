import { StatusIndicator } from "@/components/design-system/status-indicator";
import type { EvidenceResponse } from "@/lib/oqi/contracts";

// CDD-045 §11/§29 UI Truth Table -- the signature N-source experience.
// Every governed participant renders, including missing and dissenting
// ones; agreement is described as "N governed peers observed {value}",
// never as correctness. A candidate, if one exists, is always labeled
// "Candidate — not established truth" -- this exact wording is load-
// bearing and must never be shortened to imply correctness.
//
// CDD-081 §11: `finding_family` is passed down so an empty
// `participants` list can be described truthfully. OQI2 is the only
// family that populates multi-source comparison (backend
// oqi_product_experience_service.py `get_evidence()`) -- OQI1/OQI3
// legitimately never do, by design (Classification D), so their empty
// list must never render the same "no evidence" wording a genuinely
// empty OQI2 case would.
//
// WOW-I3-A-R6: evolves the flat row list into a CONNECTED EVIDENCE
// visualization -- three layers (source observations, a purely
// decorative comparison connector, and a Finding surface) built
// entirely from the real `participants` array (never a fixed 2-source
// layout) and the same real `is_conflicting`/`is_missing`/
// `is_authoritative` flags as before. The connector asserts nothing
// beyond "these governed observations are being compared as evidence
// for this finding" -- no causation, precedence, or authority. Per
// R6 §9 investigation: a real, backend-seeded human-readable business
// label ("Country of Origin", `demo_oqi_seeder.py`
// `field_label=CanonicalName("Country of Origin")`) exists for the
// Golden Thread, but belongs to a separate domain (SourceField/
// FieldValueEvidence) never exposed by any OQI API contract this page
// consumes (`EvidenceParticipant`/`FindingDetailResponse` carry no such
// field, confirmed by direct search) -- no identifier bridge connects
// them, matching CDD-081's own prior finding on this exact class of
// gap. It is therefore never hardcoded here; the Finding surface uses
// only the existing truthful "Governed source values disagree" wording.
export function EvidencePanel({
  evidence,
  findingFamily,
}: {
  evidence: EvidenceResponse;
  findingFamily?: string;
}) {
  const known = evidence.participants.filter(
    (p) => !p.is_missing && p.observed_value !== null,
  );
  const valueCounts = new Map<string, number>();
  for (const p of known) {
    if (p.observed_value) {
      valueCounts.set(
        p.observed_value,
        (valueCounts.get(p.observed_value) ?? 0) + 1,
      );
    }
  }
  const hasDisagreement = evidence.participants.some((p) => p.is_conflicting);
  // The distinct observed values among conflicting participants, in
  // participant order -- real values only, never a synthesized summary.
  const disagreeingValues = [
    ...new Set(
      evidence.participants
        .filter((p) => p.is_conflicting && p.observed_value !== null)
        .map((p) => p.observed_value as string),
    ),
  ];
  // WOW-I3-A-R5 §6: "N governed peers observed {value}" is frontend-
  // derived aggregation of the already-visible cards above it -- real
  // information when it reveals a consensus/dissent split (e.g. "3
  // governed peers observed X" alongside a lone dissenter), but pure
  // restatement when every distinct value already has a count of
  // exactly one (nothing was actually aggregated). Suppressed only in
  // that specific case -- never when it would drop a real governed
  // fact -- per CDD-081 §11/WOW-I3-A-R5 §6 Option C.
  const aggregationIsInformative =
    known.length > 0 && valueCounts.size !== known.length;

  return (
    <div>
      <h3>Source Evidence</h3>

      {evidence.participants.length === 0 ? (
        <p role="status">
          {findingFamily === "OQI2"
            ? "No source evidence has been recorded for this Finding."
            : "This finding type does not compare multiple governed sources."}
        </p>
      ) : (
        <div
          className={
            hasDisagreement
              ? "obs-evidence-comparison obs-evidence-comparison--disagreement"
              : "obs-evidence-comparison"
          }
        >
          {/* LAYER 1+2 -- source system + its own observation, structurally
              driven by the real participant array (never fixed to two). */}
          <div className="obs-evidence-sources">
            {evidence.participants.map((participant) => (
              <div
                key={participant.source_system}
                className="obs-evidence-source-card"
              >
                <span className="obs-evidence-source-name">
                  {participant.source_system}
                </span>
                <span className="obs-evidence-source-value">
                  {participant.is_missing ? (
                    <span className="obs-evidence-missing">
                      <StatusIndicator status="unknown" />
                      <span>Missing</span>
                    </span>
                  ) : (
                    participant.observed_value
                  )}
                </span>
                {participant.is_missing ? null : (
                  <span className="obs-evidence-source-caption">
                    Observed value
                  </span>
                )}
                {participant.is_authoritative ? (
                  <span className="obs-evidence-source-meta">
                    Governed authoritative source
                  </span>
                ) : null}
                {participant.is_conflicting ? (
                  <span className="obs-evidence-source-flag">
                    <StatusIndicator status="conflict" />
                    <span>Conflicting</span>
                  </span>
                ) : null}
              </div>
            ))}
          </div>

          {/* Purely decorative -- the real meaning ("these observations
              are being compared") lives in the Finding surface's own
              accessible text below, never solely in this connector. */}
          {hasDisagreement ? (
            <div className="obs-evidence-connector" aria-hidden="true">
              <span className="obs-evidence-connector-line" />
              <span className="obs-evidence-connector-stem" />
            </div>
          ) : null}

          {/* LAYER 3 -- the one real, already-computed finding this
              comparison supports: a cross-source disagreement. Never a
              claim about which value is correct. */}
          {hasDisagreement ? (
            <div className="obs-evidence-finding" role="status">
              <span className="eyebrow">Detected Conflict</span>
              <h4 className="obs-evidence-finding-title">
                Cross-Source Consistency
              </h4>
              {disagreeingValues.length > 1 ? (
                <p className="obs-evidence-finding-values">
                  {disagreeingValues.join(" ≠ ")}
                </p>
              ) : null}
              <p className="obs-evidence-finding-caption">
                Governed source values disagree
              </p>
            </div>
          ) : null}
        </div>
      )}

      {aggregationIsInformative
        ? [...valueCounts.entries()].map(([value, count]) => (
            <p key={value} className="obs-evidence-aggregate">
              {count} governed peer{count === 1 ? "" : "s"} observed {value}
            </p>
          ))
        : null}

      {evidence.candidate ? (
        <div className="panel" style={{ marginTop: "1rem" }}>
          <span className="eyebrow">Remediation candidate</span>
          <h4 style={{ marginTop: "0.25rem" }}>
            {evidence.candidate.proposed_value}
          </h4>
          <p style={{ color: "var(--muted)" }}>
            Basis: {evidence.candidate.supporting_participant_count} governed
            peer
            {evidence.candidate.supporting_participant_count === 1
              ? ""
              : "s"}{" "}
            agree
          </p>
          <p style={{ fontWeight: 700 }}>Candidate — not established truth</p>
        </div>
      ) : null}
    </div>
  );
}
