# Architecture

[INDEX.md](INDEX.md) is the sole authoritative registry for released CTEC architecture.

Do not use architecture documents from Downloads folders, attachments, legacy `docs/` locations, or feature branches. The `released/` directories are immutable release baselines; changes require a new release and a coordinated registry update.

Each baseline has an authoritative Architecture Release Manifest containing governance metadata and SHA-256 checksums for every artifact in that baseline. Run `make verify-architecture` before release, merge, or architecture validation. The manifest excludes only itself because a file cannot contain its own stable checksum; its checksum is recorded in the Architecture Registry.

The [Baseline v1.1 Record](released/v1.1/BASELINE-RECORD-v1.1_FROZEN.md) records its effective date, approval, artifact set, supersession, and dependency policy. Lifecycle status is singular. Currentness, authority, disposition, and baseline membership are separate governance properties. Development artifacts are non-binding even when retained in a release package.

The [Architecture Dependency Matrix](released/v1.1/DEPENDENCY-MATRIX-v1.1.csv) is the governed dependency register. Every dependency must resolve to the exact current Frozen version in `INDEX.md`. Architecture verification fails on missing, Superseded, Development, unapproved, or version-mismatched dependency rows and on stale dependency references in authoritative artifacts.
