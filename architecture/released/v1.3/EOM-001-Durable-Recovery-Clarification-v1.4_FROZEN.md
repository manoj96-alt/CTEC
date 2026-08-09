# EOM-001 — Durable Recovery Clarification

Version: 1.4  
Status: FROZEN  
Supersedes: EOM-001 v1.3  
Approval: CDD-012 bounded governance decision

EOM orchestration continues to execute ERM → SRM → ASM → KRM → DRM → GRM sequentially. Durable recovery does not alter that order or any business gate.

An immutable execution attempt terminates once Completed or Failed. Retry/replay creates a linked attempt under the same logical execution. A recovery coordinator may reuse a prior completed stage only after validating its atomic checkpoint, immutable output, contract compatibility, provenance, and absence of uncertain side effects. It resumes at the first stage lacking a valid completed checkpoint. A business-gated Completed attempt is never converted to Failed or resumed into downstream capabilities.

The coordinator interprets only technical checkpoint metadata. It never interprets or recreates CDD-011 business semantics.
