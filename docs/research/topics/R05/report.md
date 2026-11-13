# R05 — Reusable generation without recreating engines

Research decision ready for independent review. The canonical task triplet was missing at takeover. This study inspected actual contemporary generator code, tested a real pinned generator and distinguished raw signature generation from NativeWeave-specific lifecycle semantics.

## Decision and comparison

Use the adapter's explicit Rust C exports as representation authority, a narrow semantic sidecar for ownership/thread/retirement information, and deterministic maintainer-side generation/validation. Reuse .NET LibraryImportGenerator for static stubs. csbindgen may supply raw Rust-to-C# extraction; enforce export completeness independently. No generator owns a managed SQL AST, dialect, network engine or per-entity Rust compilation.

| Candidate | Inspected evidence | Decision for present design |
|---|---|---|
| csbindgen1.9.8 `b9eb1e84…` | Parser unsupported-type handling; emitter; all crate source compiled for probe | Useful narrow raw extraction; omission must fail inventory gate; lifecycle wrappers still needed |
| .NET11 LibraryImportGenerator | Fixed source incremental pipeline; actual native import/AOT execution | Reuse maintained stub generation, with bindings present before compilation |
| cbindgen `2b757a22…` | Official source repository documentation | Rust→C header, suitable independent C-layout route; no claimed generator execution here |
| bindgen `0d213bc3…` | Official example/direction and libclang inputs | C/C++→Rust; useful for C engines, not a C# emitter |
| UniFFI `482095c1…` | Official backend list; actual Future scheduler/waker/result code and tests | Reuse design insights; official C# implementation is third-party; do not force its runtime model |
| Interoptopus `c6774879…` | Real C# inventory mapping, Task model and source-tree structure | Viable high-level alternative; its generic surface alone is not evidence of D04/D06 conformance |
| Diplomat `f8259ad0…` | Real .NET backend, ownership comments, callback disabled code, raw templates | Important current alternative, but callback and cross-thread disposal profile does not satisfy NativeWeave unchanged |

Full SHAs/paths/ranges are in [source-inspection](../../../../verification/interop-completion/source-inspection.json). Branch snapshots for alternatives are research snapshots, not release dependencies. Names or README claims are not treated as proof that a backend is absent or safe.

## Actual generator experiment

The pinned csbindgen1.9.8 crate was fetched as exact Git blobs, checked against GitHub identities and built using Rust1.100 with a saved Cargo.lock. The same `nw_ic_validate_extent(u64,u64,u64)->u32` export is consumed through csbindgen-generated DllImport and framework LibraryImport. Sixty boundary combinations agree in normal mode and sixty in an actually published Linux Native AOT executable. Source, generated code, dependency lock, raw build/run output and native/AOT binary hashes are preserved under `verification/interop-completion/binding-linux`.

A parser-only Rust input deliberately contains an unsupported tuple parameter. csbindgen exits successfully, prints an unsupported-type message and omits that function from generated C#. The probe observes the absence and records that the required-export inventory must reject it. A tool's successful process exit is therefore insufficient as the binding build gate. This experiment is intentionally narrow; it does not execute every backend, arbitrary upstream type shape or a product wrapper generator.

## Newly corrected assumptions

Diplomat currently has a .NET backend. The user guide says LibraryImport, while the pinned actual raw method/destructor templates emit DllImport; the latter is the implementation evidence. `gen/callback.rs` explicitly documents unfinished callbacks and disabled support. `dotnet/mod.rs` states applications must synchronize cross-thread calls/disposal. It would be incorrect both to claim no C# backend exists and to import its ownership runtime as though it already provided NativeWeave's logical gate and asynchronous quiescence.

Interoptopus's source is now a pass-based inventory model, not just an obsolete archived backend. Its function mapper defers missing type mappings and its Task model represents a managed Task return shape. Acceptance still requires checking the final emitted export inventory and actual retirement/lifetime semantics. Its own performance claims are not NativeWeave benchmark evidence.

## Design constraints and failure handling

The semantic sidecar describes only what source signatures cannot: owner/release pairing, borrowed input end, mutable access, parent-state lease, callback cookie/drain, operation state functions and thread affinity. It is validated build data and does not impose a runtime parser or universal request format. Unknown schema/type/capability, missing destructor, unsupported export, inconsistent calling convention or differing layout stops the build before packaging.

Generated managed methods maintain logical admission and SafeHandle references in try/finally. Async code follows D06 rather than being synthesized from the mere presence of `async` in Rust. Entity metadata remains an application-side descriptor; adding an entity never changes native engine code. A proprietary deep adapter/fork is justified only by a concrete missing engine seam, not by generator inconvenience.

## Closure and future task boundaries

D03 gives implementable normalized fields, generation stages, diagnostics and test oracles. A09–A12 own the narrow production generator/validation; R06 establishes Roslyn constraints. Mature tool reuse is preferred where its verified profile fits, and conformance allows replacement without changing the public domain APIs. Building and validating the full product emitter remains implementation, while the comparative source findings and working raw binding route close the architectural selection question. No end-user Cargo, complete LINQ provider or giant runtime is introduced.
