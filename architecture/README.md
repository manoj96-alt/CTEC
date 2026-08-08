# Architecture

[INDEX.md](INDEX.md) is the sole authoritative registry for released CTEC architecture.

Do not use architecture documents from Downloads folders, attachments, legacy `docs/` locations, or feature branches. The `released/` directories are immutable release baselines; changes require a new release and a coordinated registry update.

Each baseline has an authoritative Architecture Release Manifest containing governance metadata and SHA-256 checksums for every artifact in that baseline. Run `make verify-architecture` before release, merge, or architecture validation. The manifest excludes only itself because a file cannot contain its own stable checksum; its checksum is recorded in the Architecture Registry.
