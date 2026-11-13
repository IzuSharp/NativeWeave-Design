# D10 — Precompiled Engine packaging and upstream maintenance

Contract: **C-BUILD-001@0.3.0**. Status: complete design candidate; the registry holds the reviewed version/hash and acceptance. Product release verification remains separate. Existing R13/R14/R18/D10/A13–A16/A22/A24 and B24 own this work. This is the build/maintenance implementation specification, not an additional task graph.

## 1. Separate maintainer and application builds

NativeWeave maintainers build the native Engine and Adapter, lock Cargo dependencies/features, run per-target ABI/source/behavior tests and publish verified native assets through NuGet. Ordinary C# consumers restore those assets and compile their own C# application. Adding a Student/User/Order type whose columns and operations use already supported native capabilities must not invoke Cargo, create Rust Entity definitions, wait for external CI or download a compiler.

`dotnet build` and `dotnet run` are normal development commands; JIT development is permitted, but formal publication requires Native AOT execution. Packaging must resolve the development host's native asset without requiring an explicit RID on every local command. `dotnet publish -r linux-x64 -p:PublishAot=true` and the Windows equivalent produce the formal targets. The recovered early prototype used explicit RID arguments. The new R13/R18 real codec fixture now executes RID-free independent NuGet development and explicit-RID AOT on Windows/Linux with Rust absent from the consumer's effective tool environment. A pristine machine without Rust remains a distinct A16 release gate.

A custom native extension, new Rust codec/operator, GPU shader compiler profile or unsupported platform may legitimately need a separately built maintainer/custom-engine package. That exception must be explicit; it cannot silently become the default for an ordinary entity or predicate value.

## 2. Package boundary and loading

Keep managed facade/generator packages and Engine native asset packages version-coordinated but independently identifiable. NuGet assets use `runtimes/<rid>/native/`; the managed facade uses source-generated/static imports against the agreed C ABI. Select a supported asset through runtime/native loading rules or accepted static linkage, not current-directory search or an arbitrary environment-supplied DLL. Validate engine identity, ABI and capability profile before use.

Windows and Linux native binaries, dependency closures, C runtime requirements and CPU baseline are tested separately. Static-link targets require explicit linker/export/retain-symbol rules and cannot be inferred from desktop dynamic-library success. iOS/Android remain R33/D21 platform research, not automatically supported by a desktop NuGet.

No schema-specific Rust library is emitted in the ordinary database profile. C# metadata and DTO constructors are compiled into the managed application; native tables/columns/values are runtime data. A custom SeaORM static Entity package remains a separate opt-in build product, not a dependency of every application.

## 3. Generator and build ordering

Incremental C# generators emit only deterministic C# metadata, descriptors and DTO code from declared source inputs. They must not run Cargo, contact a database/network, mutate external source trees or require another generator's generated syntax in the same compiler pass. Handwritten static descriptors are a supported fallback for generator-unfriendly situations, **not** a dynamic/reflection fallback. The shared generation schema is versioned and tested independently of SQL translation.

Maintainer builds may invoke Cargo from explicit build targets with pinned inputs and target matrices. Build tools own this orchestration; source generators do not. A generator package's analyzer target and compiler compatibility need separate test fixtures from a net11 application target.

## 4. Upstream-to-Adapter source map

For every published Engine retain: upstream repo URL, version tag and full commit; package version and checksum; Cargo.lock and enabled features; compiler/linker/OS/CPU target; Adapter commit and ABI; patched symbols and patch hashes; upstream tests relied upon; NativeWeave differential fixtures; native artifact hashes; license/NOTICE and dependency inventory. A Git tag and a crates.io package are **different identities** until their relationship is checked. Store both when source research uses one and compilation uses the other.

Private-source dependencies additionally list visibility, source locations and behavior assumptions. `pub(crate)` access cannot be achieved through a separate crate without an upstream change or controlled source integration. No private layout or Rust ABI is a compatibility contract.

## 5. Upgrade process inside existing tasks

R14 researches the next appropriate stable/security revision; A22/B24 test it on an isolated update branch. Do not automatically promote a new release. Compare public signatures, touched internal source paths, feature defaults, minimum compiler/target requirements, transitive dependencies and license/security changes. Run upstream relevant tests and NativeWeave native-versus-adapter differential tests, old/new ABI consumers, query SQL+parameter/result oracles, cancellation/fault/race tests and full-workload performance/memory regressions.

A security update that changes behavior still requires a documented compatibility decision; silently keeping a vulnerable old pin is not a maintenance strategy. For a fork maintain a small ordered patch queue against an exact upstream commit, upstream issue/PR references, a named ownership role, rebasing tests and an exit/retirement condition. Evaluate public-API replacement when upstream adds the missing seam. Preserve upstream license obligations and audit the entire packaged closure; this document does not certify a completed legal/security audit.

Automated release detection may open an update investigation, never publish/merge a production Engine solely because a version number increased. No scheduled watch has been activated in this session.

## 6. Compatibility and differential gates

ABI-major mismatch is rejected. Compatible minor changes add optional capabilities without changing existing layouts or ownership. Expanded native feature profiles do not retroactively make old packages support a new operator. Document SQL dialect and error-semantic changes as observable behavior even when the C ABI is unchanged. C# API stability is managed separately from upstream Rust's generics and minor-version internals.

Fixtures compare direct pinned Rust calls with C# facade calls: SQL text and parameters separately, database results/errors, streaming order, NULL/collation, rollback/unknown-commit outcomes and buffer reclamation. Performance comparisons use the same database/protocol/workload/hardware and record uncertainty; no unexplained percent threshold is invented. Resource bounds and correctness negatives are hard requirements regardless of benchmark speed.

## 7. Acceptance matrix

A13: deterministic maintainer build, no generator side effects, reproducible manifest. A14/A15: real native build/load and AOT consumers on their own OS. A16: NuGet restore/asset selection and dependency provenance. A22: old/new packages, ABI/capability rejection, patched source changes. B24: complete mandatory Rust database/ORM/server package combination plus the chosen optional-consumer protocol packages.

Required consumer fixtures include a pristine supported machine without Rust, offline restore after a permitted package cache population, RID-free `dotnet build/run`, explicit-RID AOT publish/run, adding an entity/projection/parameterized dynamic predicate with the **same native binary hash**, wrong-entity compile failure, missing asset/wrong arch/ABI/capability failures, trimming diagnostics and source-generator versus handwritten-static parity. Windows and Linux are distinct rows. No real package has been published by this research.

## 8. Recovered evidence and gaps

[Recovered evidence](../research/source-driven-evidence/README.md) supports Linux x64 local NuGet consumption with explicit RID, real Native AOT/SQLite execution and native binary reuse for a second C# entity. That historical run did not validate RID-free restore, Windows, a production generator, production streaming or clean-machine toolchain absence. Current R13/R18 and verification/completion-ci separately add real two-platform RID-free codec consumption and unchanged-native application edits; they do not retroactively change the old run's scope. Keep these obligations in A16/B10/B12/B24; do not convert the research artifact into an accepted release manifest.


## Rust 1.100 maintainer baseline and Cargo changes

Use exact stable Rust/Cargo1.100.0 and edition2024 for new maintainer builds; record `rustc -Vv`, Cargo identity, target and locked dependency closure. Existing historical evidence retains its original compiler. Crates that use the new standard-library APIs declare rust-version1.100; an upstream's lower MSRV is not a claim that the complete NativeWeave feature matrix compiled. See [R01](../research/topics/R01/rust-1.100.md).

Resolve native output via Cargo `--message-format=json` compiler-artifact records; intermediate build-dir layout changed and is not an interface. Separate per-worktree intermediates from final target assets; key reusable caches by toolchain/host/target/profile/features/lockfile. Workspace-path-hash isolation is not a cache hit or concurrency guarantee. Do not run Cargo in C# generators or normal consumers.

Use Cargo's stable unused_dependencies lint for owned crates and deliberate target/feature coverage; dev-dependencies and feature-only dependencies need separate review. Maintainer dependency-update default cooldown is7days (policy choice, not a security guarantee); keep `cargo build/test --locked`. Locked versions and missing publish timestamps are not protected by that age filter. Explicit emergency/security overrides require reviewed provenance, lockfile diff and regression evidence. No automatic production upgrade or blanket nightly feature gate.

## 9. Release manifest and trust boundary

A13/A16 emit a deterministic manifest per Engine/RID. Its schema includes:

```json
{
  "schema_version": "1.0",
  "engine_id": "codec",
  "managed_package": {"id": "NativeWeave.Engine.Codec", "version": "version-at-build"},
  "native": {"rid": "linux-x64", "path": "runtimes/linux-x64/native/libnw_codec.so", "sha256": "computed-at-build"},
  "abi": {"major": 1, "minor": 0, "required_capabilities": ["owned-buffer"]},
  "inputs": {"adapter_commit": "full-commit", "lock_sha256": "computed-at-build", "features": [], "rustc_verbose": "captured-output"},
  "provenance": {"builder_identity": "reviewed-identity", "subject_digest": "computed-at-build"},
  "licenses": {"inventory_path": "licenses.json", "notice_path": "NOTICE"}
}
```

This is a schema illustration, never an acceptance/evidence record. Reject duplicate Engine/RID
entries, noncanonical archive paths and missing required identities. Final artifact hashes are
computed after packaging; do not create circular hashes by embedding a package's own hash in its
bytes. Store package digest in the external signed release/provenance record. Internal native-file
hashes belong inside the package manifest.

An archive reader or SHA comparison does not authenticate a publisher. A22 defines allowed builder
repository/workflow/ref and signing identity, expected subject digest and trust roots. Keep signature,
identity and semantic compatibility checks distinct. Do not enable permissive identity patterns or
ignore transparency checks simply to make verification pass. Signing credentials and organization
release policy are supplied during actual release setup; no credentials are embedded in research.

Use Cargo metadata/lock and exact linker closure to enumerate packaged dependencies. The inspected
Syft Cargo.lock/auditable-binary catalogers are optional SBOM helpers; a stripped binary scan is not
proof of complete Rust dependencies. Export a standard SPDX/CycloneDX representation when tooling
cost is justified, retain exact license texts/NOTICES, and report unverifiable source/provenance
instead of filling placeholders. D31 binds the same manifest to upgrade and rollback tasks.

## 10. Error, concurrency and staged publication

Each worktree has independent output/staging directories and deterministic build inputs. A shared
cache is an optimisation keyed by toolchain/host/target/features/lock; do not use it as authority for
artifact identity. Publication stages a complete version and verifies every declared file. Atomic promotion applies
only to local staging and the release manifest/catalog, not to multiple NuGet/crate registry uploads.
Publish immutable dependency packages first, verify the whole set, then expose the release catalog.
An interrupted upload can leave a partial package set: resume only after verifying the existing payload and permitted signing identity as specified below,
or use a new version; never overwrite an already published version or advertise a complete release
before every required package is available. Failed/cancelled builds remove or quarantine their incomplete staging result;
old package versions remain immutable. Concurrent maintainers cannot overwrite the same version.

The consumer holds an Engine module lease before creating domain resources. Bootstrap rejects bad
ABI/capability/architecture before any domain owner transfers. Missing asset diagnostics include
Engine/version/RID and a supported installation path, not a search through arbitrary directories.
A05 supplies error translation; A03/A07 supply safe instance retirement. A package upgrade is a new
process/deployment in the initial profile, not hot-unloading a DLL with live callbacks.


### Exact package closure and incomplete publication

The initial profile permits only a release-validated closure of NativeWeave-owned facade, generator, native Engine and selected protocol package versions. The release record enumerates each package ID and normalized version, its direct owned-package dependency edges, Engine/RID/ABI/capability profile, and native payload hashes. Owned-package edges use exact NuGet ranges such as `[1.2.3]`; bare `1.2.3` means a minimum and is insufficient. Versions need not be numerically identical across every package, but each chosen version must equal its explicit closure entry. Do not apply an unreviewed exact pin policy to unrelated ecosystem dependencies. [NuGet version ranges](https://learn.microsoft.com/en-us/nuget/concepts/package-versioning)

Exact dependency ranges alone are not an enforcement boundary: a direct application reference may override a transitive constraint and produce NU1608. A16 supplies a build-transitive validation target, after restore and before build/publish, that compares the resolved NativeWeave package graph and selected native asset metadata against the supported closure and emits a hard package-closure diagnostic on mismatch. Release fixtures treat NU1605/NU1608 as errors and test direct overrides and suppressed warnings; the closure check must still reject the invalid combination. Runtime bootstrap independently rejects an incompatible Engine identity/ABI/capability/RID before publishing domain handles. This is compatibility enforcement, not protection from a deliberately modified application. [NU1608](https://learn.microsoft.com/en-us/nuget/reference/errors-and-warnings/nu1608)

Before public upload, restore the complete closure from isolated staging and execute the declared Windows/Linux consumer and AOT profiles. A partial-set fixture must fail rather than selecting a newer or unrelated native dependency. Upload immutable dependencies before their facades, record every per-package result, then read back and restore the whole declared closure from the destination before marking the release available. A successful per-package HTTP response does not prove this project-level closure is consumable. Nuget.org rejects an existing ID/version with 409; a retry/skip-duplicate result is never by itself proof of byte identity. Read back and validate the existing item before resuming. Any payload or identity conflict stops that release and requires a new version; do not overwrite or silently substitute it. Other feeds require their own documented overwrite/delete policy. [Push and Delete](https://learn.microsoft.com/en-us/nuget/api/package-publish-resource)

Record the upload archive SHA-256 and observed downloaded archive SHA-256 separately. Where repository signing/re-signing legitimately changes the signature envelope, verify allowed author/repository identities and compare the accepted unsigned payload entries, nuspec/dependencies, internal manifest and native-file hashes under a defined package-signature verifier; never ignore arbitrary differing archive entries. Keep the external signed release record bound to the validated payload and its observed registry artifact. The package's own full archive digest remains external to avoid circular hashing. [Repository signatures](https://learn.microsoft.com/en-us/nuget/api/repository-signatures-resource)

An incomplete release remains unadvertised in the project catalog; this does not prevent direct installation of already uploaded leaves. Nuget.org normally offers unlist/deprecation, not removal or replacement of an existing version. Known-version restores can still obtain an unlisted package, and caches remain. Unlist/revoke catalog exposure is therefore adoption guidance, not a consumer kill switch. Correct defective payloads with a new version and preserve a tested previous complete closure for deployment rollback. Existing deployments do not hot-swap or unload their native module. [Deleting packages policy](https://learn.microsoft.com/en-us/nuget/nuget-org/policies/deleting-packages)

