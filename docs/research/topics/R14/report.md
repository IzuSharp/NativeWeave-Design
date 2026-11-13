# R14 — Package identity, compatibility, provenance and upgrades

Author: `/root`. Research/design scope; signing a production release and enforcing organization trust are future A16/A22/B24 work, not actions taken by this research.

## Real sources and distinctions

NuGet.Client `7e935f9c72b287adc13b9f42fd7b3bdcaa1500e7` `PackageArchiveReader` owns its archive stream, disposes it on failed ZIP construction, and exposes package file/stream enumeration. Opening a valid archive does not establish trust or ABI compatibility. SDK asset resolution is the pinned R13 source; package version, Rust crate version, C ABI major/minor and C# semantic version are four related but distinct identities.

Cargo's pinned dependency documentation distinguishes git/path/registry locations and publication constraints; a git checkout is not the crates.io tarball. Retain crates.io checksum, full source commit when provided, selected features, lockfile and actual compiled metadata. `cargo metadata --locked` describes the resolved graph, while the lockfile may include packages not built for a particular target/features. Build an exact packaged-closure inventory, not an unqualified count of every lockfile entry.

Syft `af5b1fa52ff415605886ebb22e2bc2bd5dff7151` actually has a Cargo.lock cataloger and a separate cargo-auditable binary cataloger. Its parser resolves dependency strings by name/version/source. A stripped ordinary Rust binary cannot be assumed to contain all dependency identities just because a scanner accepts it. Select Cargo metadata/lock plus native linker/dependency inspection as authoritative build inputs; Syft is an optional SBOM-format/export cross-check, not a substitute for that inventory.

Cosign `6181e75677cc4719e845fa23d0ef8a936e883aa0` verification code separates key verification, identity policy, trusted material, claim verification, offline mode and transparency-log/SCT options. A hash is integrity against a known expected value, not provenance; a cryptographically valid signature without the expected builder identity and subject digest is insufficient. Avoid permissive identity regexes or IgnoreTlog/IgnoreSCT as unexplained defaults. No Cosign command or external trust/signing operation was executed here; the evidence is source analysis of candidate maintainer tooling.

## Executed inventory and consumption

The real codec package in R13/R18 records the built native SHA, NuGet SHA and package entries, and confirms the package's native file hash equals the compiled cdylib. The same asset survives ordinary C# changes and AOT publishing. A generated inventory records miniz_oxide0.9.1 (MIT OR Zlib OR Apache-2.0) and adler2 2.0.1 (0BSD OR MIT OR Apache-2.0), declared repository identity, crate checksum and source metadata. These declarations are evidence to review, not a completed organization-wide legal audit.

A local research NuGet is not a signed or externally published release. Failed, superseded and successful runs retain their source snapshot and output hashes. Future official packages add trust policy, reproducible build investigation, dynamic runtime dependencies and packaged NOTICE/license material; the finite fixture does not manufacture those facts.

## Concrete version-combination policy

| Managed requirement / native package | Decision |
|---|---|
| Same ABI major, available required capability bits and compatible semantics | Permit after bootstrap and descriptor validation; test old managed/new native and new managed/old native separately |
| Same ABI major, newer optional fields | Read only advertised supported prefix, leave absent fields at defaults, never overrun caller capacity |
| Same ABI major but missing required feature/codec/dialect capability | Explicit NotSupported before operation ownership transfers |
| Different ABI major, pointer width, architecture or incompatible semantic change | Reject; install a compatible package, never reinterpret the layout |
| Same package version but unexpected native digest/provenance | Reject release/installation verification; preserve suspect artifact for investigation |
| Upstream change with unchanged ABI but changed SQL/NULL/error/stream behavior | Treat as observable semantic compatibility change, run differential oracles and document version decision |

Bootstrap is D02; error status authority is D08. This table does not introduce a second handshake implementation.

## Upgrade and rollback procedure

1. Open an isolated maintainer update branch/worktree; pin upstream source, release/crate checksum, Cargo.lock, selected features and patch queue. Compare public and private seams actually used, target/MSRV changes, dependency/licenses/advisories and defaults.
2. Build both OS profiles. Run upstream relevant tests where feasible, NativeWeave direct-native versus facade oracles, ABI old/new combinations, invalid capability/layout negatives and cancellation/retirement/fault tests. Retain failed attempts.
3. Compare complete workload performance/memory with uncertainty under D13. A hot microbenchmark cannot approve an altered transaction or body lifetime.
4. Review the exact candidate artifacts, provenance and compatibility declaration; publish immutable versions. Roll back by selecting the last known compatible package set, not overwriting a version or silently changing native bytes.
5. A fork retains exact upstream base, ordered minimal patch hashes, owner, security update path, upstream issue/PR references and an exit condition. Re-evaluate public APIs on every upgrade.

Dependency-age policy is configurable, initially seven days for routine new resolution; existing Cargo.lock and missing timestamp exceptions are documented in R01. Emergency security updates may bypass the cooldown only with a recorded reason and regression review. Cooldown is not an authenticity or vulnerability guarantee.

## Final research conclusion

Use a small explicit provenance/compatibility manifest integrated into existing package and ledger workflows. Do not introduce an always-running release service or product Core dependency on SBOM/signing tools. D10/D31 define the precise schema and update obligations. Product signing, pristine-image consumption and final release dependency closure remain explicit Delivery gates. There is no unresolved architectural requirement to rebuild native code for ordinary application models.
