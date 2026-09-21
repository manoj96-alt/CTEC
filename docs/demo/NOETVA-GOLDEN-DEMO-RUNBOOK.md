# Noetva Golden Demo — Operator Runbook

CDD-085 (Noetva Demo Readiness Golden Story Architecture) + CDD-085-Artifact-Authorization-G-R1
(Entity Resolution Flush-Ordering Amendment). This is an **operational runbook** for a presenter or engineer
running the Golden Demo — exact commands, exact screen order, exact spoken lines, known limitations. It is
**not** the polished CEO/VC Presenter Playbook; that memorization/speech document is created after
NOETVA-DEMO-READINESS-VM independently certifies the exact product behavior and screen journey. Do not extend
this document into that one.

## 1. Startup

```
make run                    # docker compose up --build (Postgres, Keycloak, backend, frontend)
```

Wait until the backend log shows `[entrypoint] starting server...` and the frontend is reachable.

## 2. Reset — get to a known-clean Golden state

```
CTEC_DEMO_RESET_ALLOWED=true make demo-reset
```

This downgrades the schema to base, upgrades back to head, and re-seeds Ontology → Blueprint → the Golden
Demo tenant (`DemoOqiSeeder`) from scratch. It refuses to run (no destructive action, non-zero exit) unless
both `CTEC_DEMO_RESET_ALLOWED=true` **and** the database host is on the local/demo allowlist
(`localhost` / `127.0.0.1` / `postgres`) — see §7 (Troubleshooting) for what a refusal looks like.

## 3. Verify — confirm the Golden state before presenting

```
make demo-verify
```

Expect all 11 checks to print `[PASS]` and the final line `demo-verify: ALL CHECKS PASSED`, exit code 0. If
anything prints `[FAIL]`, do not present — re-run `demo-reset` (§2) and `demo-verify` again; if it still
fails, stop and escalate (this command makes zero database change, so it is always safe to re-run).

## 4. Login

Sign in at the app's login screen with the demo presenter account. Authentication is real Keycloak
Authorization-Code + PKCE — there is no bypass.

## 5. Screen sequence and spoken lines

The story: **Maya, Director of Supply Chain Intelligence, ten days before the Aurora X1 launch**, asking one
question — *"Are we ready to launch Aurora X1?"*

| # | Route | Presenter says | Presenter points at |
|---|---|---|---|
| 1 | `/quality/findings` (Findings list) | "Ten days out from the Aurora X1 launch, our governed data quality system already knows something is wrong." | The open OQI2 Finding on **Meridian Cell Components**' Country of Origin. |
| 2 | `/quality/findings/[findingId]` — Evidence tab | "SAP says the supplier is US-based. PLM says Mexico. Two governed systems, two different answers — and neither is assumed correct." | The two source cards, the "Governed source values disagree" surface. |
| 3 | Evidence tab → **View resolved entity** link | "This isn't a guess about who the supplier is — it's a resolved, governed identity." | The new contextual link (shown only on OQI2 findings). |
| 4 | `/data/entity-resolution` | "Meridian Cell Components is one governed entity, resolved from both SAP and PLM." | The resolved entity record. |
| 5 | Ontology Studio → traverse Meridian Cell Components → Aurora X1 Battery Cell → Aurora X1 Bill of Materials → Aurora X1 | "This supplier isn't just a name in a table — it's structurally connected to the exact product launching in ten days." | Each hop of the `supplies` → `usedIn` → `defines` chain. |
| 6 | Finding detail → Business Impact tab | "That's why this Finding is rated HIGH criticality — it's tied to Aurora X1 Supplier Qualification." | The Criticality = HIGH badge. |
| 7 | Finding detail → Reliance tab | "And Aurora X1's reliance on this supplier is AT RISK, precisely because of the open conflict." | RELIANCE_AT_RISK state. |
| 8 | Finding detail → Agent tab | "Before anyone touches this, an agent could investigate — but it hasn't been invoked. No fabricated analysis, ever." | The honest "not invoked" state. |
| 9 | Finding detail → Remediation tab → Prepare | "The system proposes real candidates from the real conflicting evidence — US and MX — never a fabricated single answer." | Both candidates, each with its supporting basis. |
| 10 | Remediation → Authorize | "A named human — never the same person who requested it — must authorize this. No anonymous or self-approval." | The authorization requiring a distinct `decided_by`. |
| 11 | Remediation → Report execution | "Once the change is made externally and reported back, the system re-evaluates." | The case moving to `EXTERNAL_EXECUTION_REPORTED`. |
| 12 | Back to Finding detail | "**The Finding is still OPEN.** Reporting an execution is not the same as fixing the underlying data — until SAP and PLM actually agree, the conflict stands. Remediation is not resolution." | The Finding status, still OPEN. This is the signature moment — state it plainly, do not apologize for it. |
| 13 | `/quality/findings` → filter to Uniqueness | "Separately, the system caught something else: two Product records that look like they might be the same thing — Aurora X1 and AURORA X1." | The Uniqueness Finding for the pair. |
| 14 | Uniqueness Finding detail | "This is a candidate, not a fact. Confirming it never merges the two records — there is no merge, no auto-resolution, no fuzzy-matching shortcut here." | The "Candidate — not established fact" label; absence of any merge/deactivate control. |
| 15 | Return to `/quality/findings` (Overview) | "Ten days before launch, Noetva didn't just flag a data problem — it connected that problem to the exact product, the exact business impact, and gave a governed, human-authorized path forward, all while refusing to fabricate certainty it doesn't have." | The full findings list, Aurora X1's Finding visible. |

## 6. Reset after presentation

```
CTEC_DEMO_RESET_ALLOWED=true make demo-reset
make demo-verify
```

Always reset immediately after presenting — the remediation authorization/execution-report state and any
steward adjudication made live during the walkthrough are real, durable writes; only a full `demo-reset`
clears them for the next presentation.

## 7. Known limitations — disclose, do not route around

- **Integrity Finding-detail 404** (tracked separately, `NOETVA-INTEGRITY-FINDING-DETAIL-R1` or equivalent
  future governed phase): `ORPHAN_REFERENCE` / `RELATIONSHIP_CARDINALITY_VIOLATION` /
  `MISSING_REQUIRED_RELATIONSHIP` findings list correctly but 404 on their own detail route. **Never navigate
  into an Integrity finding during a live demo.** The Golden Demo's own route sequence above never requires
  it.
- **Agent boundary**: the Agent tab will always show "not invoked" for the Golden Finding — there is no
  production path that ever executes an agent investigation automatically or on a demo-only trigger. This is
  a deliberate, honest limitation, not a bug to work around.
- **Ask CTEC**: classified **EXTENDED DEMO ONLY** by CDD-085 pending live confirmation. The example question
  "Which products depend on Meridian Cell Components?" has since been live-verified to answer correctly
  (Aurora X1) — safe to use as an *extended*, optional demo beat after the primary Golden path above, but the
  primary Golden Demo does not depend on it and this classification is not changed by this runbook.
- **Gate F / Supply-Chain-Impact page** (`/supply-chain-impact`): a separate, deferred system with its own
  seed data and its own supplier entities, entirely distinct from the Golden Supplier above. **Do not
  navigate there during the Golden Demo** — it is not part of this story and uses different entity identities
  that would contradict it.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `demo-reset refused: CTEC_DEMO_RESET_ALLOWED is not set...` | Env var missing/not exactly `true` | Re-run with `CTEC_DEMO_RESET_ALLOWED=true` prefixed |
| `demo-reset refused: database host '...' is not in the allowed local/demo host list` | `CTEC_DATABASE_URL` points somewhere not on the allowlist | Never override this — it is the safety boundary. Confirm you're running against the local/demo stack, not a shared environment. |
| `demo-verify` prints one or more `[FAIL]` lines | State drifted from a partially-completed prior demo, or the stack is mid-startup | Re-run `demo-reset` then `demo-verify` again |
| Evidence tab shows no "View resolved entity" link | You are looking at a non-OQI2 Finding (e.g., Integrity, Timeliness) | Navigate back to the Meridian Cell Components Country-of-Origin Finding |
| Ask CTEC returns "no governed evidence found" for the example question | Golden seed state is stale/partial | Re-run `demo-reset` — this question is live-verified to answer correctly against a freshly reset Golden state |
