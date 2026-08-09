# RSP-001 — Runtime Security, Retention, and Replay Authority

Version: 1.0  
Status: FROZEN  
Approval: CDD-012 bounded governance decision

The ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`) owns the bounded runtime-security controls for CDD-012. `EXECUTION_RECOVERY_OPERATOR` with `execution:replay` is the narrow authorized replay role/scope; it grants no business, governance-approval, tenant-administration, or unrelated runtime authority.

Replay requires valid AuthorityContext, tenant equality, reason, correlation identifier, authorization decision/reference, and immutable audit. Original authority is not transferred; original and replay authority references persist separately.

PostgreSQL connections require encrypted transport and storage relies on platform-standard encrypted volumes/services. Application records store no credentials, tokens, secrets, or full authentication material. Protected handoffs may store only the minimum encrypted content required for recovery; hashes and governed references are preferred. Logs expose only safe codes and references.

Records retain seven years after terminal completion; transient non-required payload expires within 30 days. Legal hold suspends deletion. Deletion is authorized, tenant-scoped, dependency-consistent, and audited. Stricter law, contract, or frozen enterprise policy controls.
