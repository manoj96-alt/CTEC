# CDD-012 / CDD-014 — Replay Frontend Defect Authorization

Version: 1.0
Status: APPROVED FOR DEFECT IMPLEMENTATION
Lineage: Baseline v1.7 at `76ff5cc255ef5e110a163d2ee8872ef060fff145`

## Purpose

This post-freeze authorization permits the minimum browser correction needed to submit an
unchanged replay option issued by the governed CDD-012 recovery boundary and to prevent duplicate
browser submission while that request is pending. It does not alter replay semantics, authority,
tenant isolation, persistence, immutable execution history, or CDD-014 business workflow.

## Exact changed-path authorization

| Path | Operation | Governing authority | Purpose | Prohibited changes | Required validation |
|---|---|---|---|---|---|
| `frontend/components/supplier-risk/replay-dialog.tsx` | MODIFY | CDD-012 replay contract; CDD-014 frontend boundary | Preserve and submit the exact selected server-issued replay option; prevent duplicate pending submission. | No client-generated recovery metadata, authority bypass, alternate endpoint, unrelated UI behavior, deployment, or wildcard authorization. | Focused replay tests, lint, formatting, strict typing, exact-path and secret scans. |
| `frontend/tests/supplier-risk-recovery.test.tsx` | MODIFY | This authorization | Verify exact selected-option submission and duplicate-submit prevention. | No mocks that bypass the API client contract, broad frontend changes, or unrelated work-order rules. | Focused Vitest execution and contract assertions. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDS-001 exact-artifact governance; existing cumulative enforcement | Add only the two exact frontend paths and this authorization record to executable changed-path enforcement. | No directory, wildcard, prefix, deployment, runbook, evidence, manifest, or retained-path rules; no weakened or skipped checks. | Baseline architecture tests and exact diff review. |
| `docs/cdd/CDD-012-CDD-014-REPLAY-FRONTEND-DEFECT-AUTHORIZATION.md` | CREATE | Governing defect decision | Record this bounded post-freeze authority and lineage. | No new architecture baseline, business semantics, production behavior, or general unrelated-work authorization. | Documentation, exact-path, secret, and `git diff --check` validation. |

All other paths are READ-ONLY. No wildcard, directory-level, implicit-descendant, or alternate-path
authorization is granted.

## Publication sequence

This authorization and its executable enforcement must be reviewed and published before the
separate six-file replay defect implementation. The implementation PR must contain no governance
file or architecture-test change and must validate against the published enforcement amendment.

## Architecture release impact

This record is implementation authorization associated with frozen CDD-012 replay behavior and
the frozen CDD-014 browser boundary. It introduces no architecture artifact or dependency and
therefore does not regenerate the Architecture Registry, dependency matrix, architecture release
manifest, or baseline checksum register.
