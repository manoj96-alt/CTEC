# CDD-010 — Resume-From-Stage Clarification

Version: 1.4
Status: FROZEN
Supersedes: CDD-010 v1.3 runtime entry-point scope only
Approval: Closure Gate 4 replay remediation decision

The ordinary invocation entry point remains unchanged and always begins at ERM. One additional
internal entry point accepts only a server-created `ValidatedRecoveryInvocation` from the CDD-012
recovery service. It begins at the authorized stage, consumes verified predecessor output (or the
original admitted input for ERM), preserves ERM→SRM→ASM→KRM→DRM→GRM order, checkpoints the new
attempt normally, and never invokes reused stages. Caller-created recovery metadata or payloads
are rejected. No product API or business semantic is introduced.

