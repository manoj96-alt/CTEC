"use client";

import type { ProposalDetail } from "@/lib/ontology-modeling/contracts";
import { DecisionDialog } from "./decision-dialog";

// REVIEW: a read-only table of proposals. No inline editing -- every state
// transition happens through DecisionDialog's own explicit confirm actions.
export function ProposalList({
  proposals,
  onChanged,
}: {
  proposals: ProposalDetail[];
  onChanged: () => void;
}) {
  if (proposals.length === 0) {
    return (
      <section className="panel" style={{ marginTop: "1rem" }}>
        <h2>Proposals</h2>
        <p style={{ color: "var(--muted)" }}>No proposals yet.</p>
      </section>
    );
  }

  return (
    <section className="panel" style={{ marginTop: "1rem" }}>
      <h2>Proposals</h2>
      <table>
        <thead>
          <tr>
            <th>Kind</th>
            <th>Name</th>
            <th>Status</th>
            <th>Proposed by</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {proposals.map((proposal) => (
            <tr key={proposal.ontology_change_proposal_id}>
              <td>{proposal.proposal_kind}</td>
              <td>
                {proposal.proposal_kind === "CreateConcept"
                  ? proposal.proposed_entity_type_name
                  : proposal.proposed_relationship_type_name}
              </td>
              <td>{proposal.status}</td>
              <td>{proposal.proposed_by}</td>
              <td>
                <DecisionDialog proposal={proposal} onDecided={onChanged} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
