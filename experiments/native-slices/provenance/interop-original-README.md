# Recovered Interop executable slice — R03/R04/R07/R10

Continuation of native source `c6f5d5fa3ea1edad70c37ba8b114f725d8090f9e` and C# bindings `994fbd95da4ebbc51ee2772f04a43eb3956e5c58`, which existed at the actual interruption point without manifests, runner or PR. These files are retained, not regenerated. This package is a research fixture, **not an accepted production ABI or a completed A01–A07 task**.

## Exact recovery boundary

Design PR5 already merged at `7759248e8c3bb37a99481f09c690d2c9f9b49248`; Plan PR2 already merged at `2ef12b8459e8f8905f7b288f9b58393714aedfaa`. Both were observed merged on recovery; no duplicate merge is performed. Rust1.100 research and the previous Windows/Linux Rust API probe already exist in Design R01 and must not be rerun merely for recovery. This slice adds genuinely new C#/Rust integration execution.

User requirements are cumulative: ArcForges is a format reference, not a domain dependency; Database lower layers are Rust; native-backed typed Fluent and precompiled ordinary entity reuse supersede managed-default/full LINQ/schema-specific build assumptions. Current user authorization permits implementation when actual contracts/dependencies allow it; merged Plan still distinguishes research fixtures from Delivery acceptance. No old lack-of-authorization sentence overrides the current user request, and no code fixture silently accepts a missing formal contract.

The original ArcForges background was recovered from the user's Library and fully read in this session, along with the NativeWeave initial brief and accessible later corrections. Six separately attributable subagent reports remain unrecovered. No callable subagent or independent reviewer has been used. Existing source/log/model evidence is reused with its original scope; self-review is not independent review.

## Run

`python experiments/interop/run.py` on Linux x64 or Windows x64 with Rust1.100.0 and .NET SDK11.0.100 (plus platform Native AOT prerequisites). Cargo builds no third-party code for this fixture and uses the checked-in lockfile. Native asset discovery consumes Cargo JSON filenames instead of depending on Cargo's intermediate directory layout.

The runner tests native repr(C) offsets and sizes, owned and empty buffers, failed publication and contained panic rollback, synchronous reverse callback, idempotent managed Dispose, and 32 deterministic Dispose-versus-in-flight-call rounds. It packs a local NuGet; the consumer uses PackageReference (not ProjectReference), builds/runs **without a RID**, then publishes and executes an explicit-RID Native AOT binary with a runtime check that dynamic code is unavailable. Native binary, package, executable, source and logs are hashed.

## Limits

Raw pointers must be live same-module handles and released once; arbitrary stale pointers are not tested by invoking undefined behavior. SafeHandle call leases provide physical lifetime, not a single-writer protocol for a future mutable query builder. The callback is synchronous and captures no managed object. Test-only global counters/hold flags are not a Core runtime. A contained Rust unwind is not OOM recovery; Box allocation and panic=abort retain their stated limits. DropGuard performs local synchronous rollback only. This tests neither async cancellation/quiescence nor database/network behavior, long soak, sanitizers or performance.

Consumer and native compilation share one host; no claim of pristine Rust-free installation. Results are pending until the Actions artifact at the exact new commit reports success. Failed attempts remain in history. No package is published to a registry, and no main/protection/license changes are made by this workflow.
