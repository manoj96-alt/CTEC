# CDD-014 — Retained Frontend Resumption Allowlist

Version: 1.0
Status: BLOCKED UNTIL REMEDIATION PUBLICATION

The retained frontend inventory remains governed by `CDD-014-FRONTEND-IMPLEMENTATION-ALLOWLIST.md`. It must not be modified, committed, rebased, or reapplied until the trusted-admission remediation is merged and verified on remote main. After publication, the same paths may be resumed with these corrections only:

- omit `received_at` from submission contracts, forms, examples, fixtures, and generated inputs;
- continue rejecting all server-controlled timestamp input;
- regenerate or update the client contract against the corrected OpenAPI schema;
- rerun every previously authorized frontend, security, accessibility, responsive, and regression check.

Closure paths remain the existing CDD-014 work order documents, implementation evidence, and Closure Gate 5 report. All other frontend and repository paths are read-only.
