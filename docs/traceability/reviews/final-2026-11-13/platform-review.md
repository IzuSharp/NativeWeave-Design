# Final independent platform, build, Engine and performance review

Reviewer: `/root/database_review`; observed 2026-11-13T13:02:45.522675+00:00. Authors reviewed: `/root` and `/root/interop_research`. This is an actual independent delegated technical review, not another GitHub approval identity.

## Decision

**Recommend research/design acceptance** for R01, R02, R13, R14, R17, R18 and D01, D10, D11, D13, D25, D26, D31, and the four exact 0.3.0 contracts below. No unresolved blocking finding remains in this scope. Delivery stays `planned_candidate` with no product implementation authorization.

The starting remote checkpoints are Design `5bb128424259f3d9cf594b4e50d7688ad5b6541e` and Plan `7359060f88f94591b0dc41178e35701eefc8eb6d`. The decision covers the recovered working bytes and author corrections identified individually in [platform-review.json](platform-review.json), not an uncommitted future source or mutable unspecified HEAD. Root performs final acceptance/commit propagation.

## Per-task disposition

| Task | Disposition and substantive basis |
| --- | --- |
| R01 | Accept research/design: Rust1.100 stable API study and exact two-OS experiments reused; .NET11/C#15 official dated releases rechecked; isolated Runtime Async metadata and real AOT results support optional lowering, not performance. |
| R02 | Accept research/design: Static imports, closed generics and source-generated JSON supported by exact source and Windows/Linux normal/AOT restrictions runs; invalid char/bool UCO Linux failure occurs before callback body. Consumer clean-image obligation maps to A16. |
| R13 | Accept research/design: SDK native/RID asset resolution plus Cargo JSON artifacts and real separate NuGet consumer establish maintainer prebuild/ordinary C# mechanism; PATH-hidden Rust research is not pristine OS certification. |
| R14 | Accept research/design: Four identities, explicit compatibility/provenance and original package inventory are sound. Newly independently checked NuGet direct override, per-package uploads, signing-aware readback and unlist rules resolve publication semantics. |
| R17 | Accept research/design: NativeAOT external executable/ISA controls, scheduled-arrival latency, failures and memory ownership distinguish valid measurements from finite model evidence; no product performance fabricated. |
| R18 | Accept research/design: Real miniz native codec and real asynchronous Rust network domain establish heterogeneous Engine boundaries; guarded managed ownership transfer is correct by control flow with post-fix Linux regression. Product construction failure and expansion-boundary gates are explicit in A17. |
| D01 | Accept research/design: Pins initial actual OS/CPU/toolchain profile, ordinary/AOT consumption, static metadata rules and separate unsupported profiles without treating Linux evidence as Windows or clean image. |
| D10 | Accept research/design: Precise owned-package closure and post-restore hard validation survive direct version override/warning suppression; staged catalog is distinct from partial public uploads; signing and payload identities, 409 conflict, unlist and previous-complete-closure rollback are coherent. |
| D11 | Accept research/design: Small optional capabilities, source-informed adapter/fork ladder, module/owner/affinity/async boundaries and independent mature Engine conformance are actionable; no mandatory giant runtime or C# domain rewrite. |
| D13 | Accept research/design: Isolated NativeAOT execution, fair direct Rust/facade/managed semantics, explicit ISA and load/failure/resource accounting form a credible implementable measurement protocol. |
| D25 | Accept research/design: A13–A16 actual file ownership, OS acceptance closure, source/native/package provenance and detailed no-Rust/package-failure cases are consistent with D01/D10 and fixed graph. |
| D26 | Accept research/design: A17–A21/A23 fragments retain exact model/fuzz limits and real Engine cases; missing A17 deterministic construction-failure gate and codec expansion limits were fixed and rereviewed. Proof/tool/device scope remains bounded. |
| D31 | Accept research/design: A22 compatibility upgrade policy and A24 two-domain scaffold keep source/crate/ABI/API/semantic identities distinct, with scoped worktrees, existing three graphs and no automatic production promotion. |

## Findings and author fixes independently rereviewed

### FP-PLATFORM-01 — resolved

A17 did not explicitly carry the prior SR-ROOT-03 deterministic post-native-success managed-wrapper-failure obligation.

Root added exact raw-owner once-only release/no partial result/no leak/no double free and normal+NativeAOT Windows/Linux injection cases to graph, packet and D26 fragment; independently reread and compared.

### FP-PLATFORM-02 — resolved_in_product_design

The finite codec fixture uses the same 4MiB input cap for compression and decompression; a permitted incompressible raw boundary input can expand beyond that cap. Existing successful finite runs do not prove all-boundary roundtrip.

Root separated raw/compressed/decoded limits in A17. Same-profile successful compression must be decodable, otherwise compression must fail before owner publication; boundary incompressible/expansion/decoded-overrun tests required. Historical fixture/evidence not rewritten or rerun.

### FP-PLATFORM-03 — resolved

R02 evidence future-obligation text incorrectly assigned no-Rust/RID consumption to A21 instead of A16.

Author corrected that one current task-reference field to A14/A15/A16; report/Design already had correct responsibility; raw manifests untouched.

## Contract bytes

| Contract | Version | Specification | SHA-256 |
| --- | --- | --- | --- |
| C-PLATFORM-001 | 0.3.0 | `docs/platforms/support-and-aot.md` | `e84e0b449c90340f396505d61504d41a7a3305fb6a02f0e3d7b540aef2adc470` |
| C-BUILD-001 | 0.3.0 | `docs/platforms/build-package-release.md` | `06313b143b922d62a9b73ee4af2f1bc66287ef0085cb4d7ad4d82e4ef838efb0` |
| C-ENGINE-001 | 0.3.0 | `docs/extension/engine-integration.md` | `2668b398c0812bbb2c5d4f1affb4a308247abfd2940949512ed74107328d22d4` |
| C-PERF-001 | 0.3.0 | `docs/performance/methodology.md` | `61014a12b683c74b7a7f66894357b878cfe7293a4c5e1c75f1d5d97f31bac1e0` |

These recommendations accept the technical rules and future test obligations. They do not assert that a production package, pristine consumer, release signature, complete Rust/C# product implementation or long-running load test exists.

## NuGet and release semantics

The reviewed D10/A16/A22/B24 changes now make the owned NativeWeave package closure explicit. Exact `[V]` dependency edges are accompanied by hard post-restore checks of the actual resolved graph and selected native metadata; suppressing NU1608/NU1605 cannot silently permit an incompatible owned profile. This is justified by the official direct-dependency-wins rule and NU1608 example. Bootstrap independently checks ABI/RID/capabilities. Unrelated external dependencies retain a separately reviewed policy.

Publication validates the complete staged closure, uploads immutable dependencies before facades, journals every package, and restores/readbacks every required destination artifact before catalog exposure. Atomicity applies only to local staging/catalog promotion. The public API operates on individual packages and does not provide a cross-package transaction. A 409/skip-duplicate does not prove matching payload; retries verify permitted signing identity, accepted nuspec/dependency/native/payload entries and separate uploaded/downloaded archive digests. Repository signature renewal can change the envelope, so equality is signature-aware without ignoring arbitrary changes.

Unlist/deprecate affects visibility. Exact-version downloads, caches and even some floating restores remain possible; no kill switch or running-module revocation is implied. Rollback selects a previously tested complete closure and a new deployment. No package operation was executed during this review.

Primary official documents independently opened on 2026-11-13:
- [dependency-resolution](https://learn.microsoft.com/en-us/nuget/concepts/dependency-resolution): Direct-dependency-wins and project.assets.json resolved graph; no transitive exact-edge enforcement assumption.
- [nu1608](https://learn.microsoft.com/en-us/nuget/reference/errors-and-warnings/nu1608): A direct dependency may resolve outside an exact transitive constraint; warning suppression is possible.
- [package-publish-resource](https://learn.microsoft.com/en-us/nuget/api/package-publish-resource): Single-package push and nuget.org existing ID/version409; multi-package partial-failure rule is an explicit design inference.
- [repository-signatures-resource](https://learn.microsoft.com/en-us/nuget/api/repository-signatures-resource): Repository certificate policy and re-signing on revocation distinguish permitted signature-envelope change from payload tampering.
- [deleting-packages](https://learn.microsoft.com/en-us/nuget/nuget-org/policies/deleting-packages): Known exact-version and some floating restores can still retrieve unlisted versions; unlist is not revocation.

## Actual evidence and preserved limits

All 17 retained CI archive manifests were scanned: **303 `preserved:true` files** exist, match the recorded SHA-256 and are tracked by Git. There is no additional missing/ignored artifact in this scan. This is an integrity check; it does not reattribute other-domain semantic review to this executor.

For the platform/codec run set, 12 saved manifests bind **208 stdout/stderr files** and **72 recorded input entries**. All checked hashes match, including unsuccessful prior inspector input/output. The first metadata-name heuristic failed and remains `passed:false`; the corrected interface-based inspector is a separate run. No native experiment was rerun.

The corrected Runtime Async runs at CI `43390177574` source `4609bae29b0c367130a3a06b4bb9ebe3e74fd3ec` use isolated projects. Windows and Linux default assemblies contain three IAsyncStateMachine implementations; opt-in assemblies contain none, and each actual AOT executable passes ten checks. The 49,152-byte escaping-union versus zero tagged-struct observation is confined to that fixture and excludes preallocated arrays. Neither observation is a product performance result.

The codec CI `43388468147` source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80` runs three native tests, sixteen ordinary NuGet consumer checks and seventeen actual AOT checks on each OS. Those artifacts precede the managed-wrapper cleanup correction. `verification/engine-completion/linux-reviewed/result.json` (`5e7f11d0f6609fa8d37251235deda5570462c6ddceaaa2590ab01e76cab0f082`) is the corrected Linux regression; Windows post-fix execution and deterministic failure injection are not asserted. A17 now owns the exact two-platform product test. The code guard was inspected: after native success, failed `new Owner` releases the raw owner, while a successful wrapper owns the sole release path; its constructor has no throwing work after SetHandle.

The R02 restrictions fixture uses source-generated static JSON, explicit closed generic instantiations and reflection fallback rejection. CI `43388468172` saved logs show four normal and six Native AOT restrictions checks on each OS. The main native-thread callback fixture reports 10,528 normal/10,529 AOT assertions and 32 controlled rounds. Linux-only invalid char/bool UCO child processes fail with InvalidProgramException before the callback-body marker. The latter is a distinct negative, not a Windows result or proof about every invalid signature.

The ordinary codec consumer hides Cargo/rustc/rustup from discovery and has no package build hooks, but `clean_operating_system=false` is preserved. An added ordinary C# record leaves the native digest unchanged. A16/B24 still require pristine no-Rust OS consumption and runtime-only transferred deployment.

## Source review and previous independent findings

All nineteen recovered upstream source files match their recorded full SHA-256 exactly. This reviewer reread Roslyn RuntimeAsync branches, SDK native/RID assets, BenchmarkDotNet NativeAOT/ISA selection, HdrHistogram correction semantics, NuGet archive ownership and miniz compression growth/bounded-decompression ranges. Other previously read ranges remain attributed to the prior independent reviewer, with no fabricated new source-read claim. Fresh exact-commit GitHub reads also verified runtime RequiresDynamicCodeAttribute and LibraryImportGenerator against their recorded Git blob identities.

The prior real `/root/server_extensions` review is preserved. Of its 27 final frozen inputs, 23 remain byte-identical; the four changed inputs are the R14 triplet and D10, all independently reviewed here. Its findings on isolated NativeAOT execution, two codec exports versus three native tests, output-wrapper transfer and nontransactional release remain visible. Current NuGet signing-aware readback strengthens the earlier byte-equality wording without editing historical review hashes.

Official current pages confirm Rust1.100.0, SDK11.0.100/.NET11 and C#15 stable features at this observation date; memory-safety remains preview. A search cache still contained an obsolete prerelease sentence for C#15, resolved by opening the current page and the dated official GA/support entries. These moving documents are dated observations, not replacements for fixed source pins.

- [](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/): Rust1.100 stable dated release.
- [dotnet-core](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core): .NET11 STS released2026-11-10; support through2028-11-14 on dated current table.
- [csharp-15](https://learn.microsoft.com/en-us/dotnet/csharp/whats-new/csharp-15): Current freshly opened page confirms C#15/net11 stable features; memory-safety remains preview. Search cache still had outdated prerelease sentence, resolved by live page and official GA release.
- [11.0.0.md](https://github.com/dotnet/core/blob/main/release-notes/11.0/11.0.0/11.0.0.md): Official11.0.0/SDK11.0.100 GA release page; moving documentation is date-scoped, not source pin.

## Delivery readiness and integration boundary

The 24 scoped R/D/Delivery packets match their graph hashes. The D25/D26/D31 fragments match **120 shared task-detail fields** across twelve tasks. The combined 114-node start+acceptance dependency graph is acyclic. A14/A15 require the actual A07/Core closure before accepting lifecycle tests; A16 waits for both OS package profiles and A22; A24 can scaffold before final A17/A18 acceptance. These local relationships avoid using future product tests as design-acceptance prerequisites.

A13 owns shared root build manifests and narrow integration patches; other tasks retain isolated files and per-task worktrees. A17 and A18 use real heterogeneous native Engines. A21 uses separate direct Rust/facade/managed AOT target executables, honest arrivals/failures/resource counters and uncertainty. A23 keeps unavailable devices/platforms unsupported instead of simulated certified success. A22/A24 retain exact source/patch/ABI/behavior relationships without introducing another workflow graph.

D26 A19/A20 fragment consistency and bounded model/fuzz claims were checked; detailed R15/R16/D12 findings belong to the independent interop review. Server production Handler/host/body integration remains with the server tasks. This report does not widen those technical scopes or grant Delivery authorization.

The reviewer changed only these review artifacts. No specification, graph, packet, historical evidence, product repository or remote branch was altered by this executor.
