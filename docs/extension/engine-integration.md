# D11 — Source-driven deep native integration

Contract: **C-ENGINE-001@0.2.0-draft**. Status: proposed; author-side source review and limited database prototype evidence; independent acceptance pending. This revision extends existing R18/D11/A24 rather than creating another coordination system. Source reports: [SeaQuery](../research/topics/R25/source-driven-seaquery.md), [Server](../research/topics/R27/source-driven-server.md). Build/maintenance: [D10](../platforms/build-package-release.md).

## 1. Goal and non-goals

Expose mature native capabilities through a modern, typed C# application surface without porting the native engine into C#. Database execution is Rust by user requirement; Server remains an evidence-dependent choice. C# First describes application development, not a managed database fallback. Ordinary applications must not require Rust syntax or a Rust toolchain merely to add a business entity supported by the precompiled Engine's existing types and operators.

“Equivalent to writing Rust” is a direction for semantic fidelity, low adaptation cost and developer productivity, not an assertion of identical machine code, zero FFI overhead or identical memory behavior. Native AOT still has a managed runtime/GC. Fixed layouts, ownership and quiescence are necessary, not objections to the overall integration method.

Not in scope: a universal execution runtime; an engine-independent SQL/HTTP/GPU AST; runtime loading of arbitrary new managed code into an already published AOT application; blanket superiority to Rust or C#; arbitrary Rust trait objects crossing a C ABI.

## 2. Two separate layers

**Capability binding** is engine-specific, follows the native source and preserves its meaningful capability set, failure modes and resource rules. **C# convenience** supplies idiomatic types, static metadata, Fluent composition, Task/async and diagnostics. Neither layer is forced to mirror every Rust generic, nor permitted to silently replace a mature native algorithm with a second implementation.

A database Table/Column is runtime metadata in the native dynamic-query profile, while a C# `Column<TEntity,TValue>` is compile-time application type information. A server ForeignHandler is one compiled Rust implementation of the native Service interface whose route IDs and callback registrations are runtime data. Both illustrate a useful pattern: **compile the adaptation mechanism once; supply ordinary application variation as data and statically compiled C# methods**. This pattern does not prove that all GPU shaders, codecs, Rust traits or platform capabilities can vary without native compilation.

## 3. Integration depth ladder, selected by evidence

| Mode | Use | Required controls |
|---|---|---|
| Public upstream API | Default when it exposes needed semantics and cost | Pin version/features, native behavior tests and adapter contract |
| Source-informed public Adapter | Inspect internals, use public entry points more precisely | Symbol/range map, ownership analysis, account for clones and buffering |
| Upstream extension | Missing fallible API, bulk operation or semantic capability | Minimal proposal/test, released-version adoption rather than tracking an unreviewed branch |
| Compatibility patch / controlled fork | Valuable capability cannot otherwise be exposed | Exact upstream base, patch queue, licenses, differential tests, security and retirement owner |

Reading `pub(crate)` does not make it accessible to an unrelated crate. Private implementation reuse requires an upstream public seam or a compatible source patch compiled into the owning crate; it is not permission to transmute private layouts or call undocumented symbols. A controlled fork may be better than recreating an engine, but the decision needs an explicit maintenance budget and upgrade exit condition. No fork has been implemented or is required by the current finite database prototype.

## 4. Core versus Engine responsibilities

Core supplies only individually usable contracts: ABI/version/capability negotiation, owned and borrowed byte regions, resource/operation leases, callback retirement, error boundary, optional async completion, and build/package metadata. It neither owns all engine runtimes nor knows SQL columns, HTTP routing, GPU command buffers, UI widgets or business transactions.

Each Engine owns its native dependency closure, domain capability validation, runtime/thread-affinity policy, domain error classification, caches, pools, streaming budget and public C# package. An Engine may have no runtime, an instance-owned runtime or worker-affine event loop. Runtime sharing requires a measured, explicit composition; it is never a default global Tokio singleton.

For a managed-only application that imports no native Engine, no NativeWeave native library is loaded. The mandatory Rust database rule applies when the database Engine is used, not to every possible application.

## 5. Minimal module manifest

The manifest binds `engine_id`, public package version, ABI major/minor and required struct sizes, upstream repository/tag/commit, locked dependency closure and Cargo features, supported RID/link mode, CPU baseline, toolchain/build identity, native asset hash, enabled capability IDs, error categories, lifecycle/thread profile, and provenance/license references. Application model hashes may key metadata caches but must not be mistaken for a native binary's compiled entity inventory.

ABI-major or required-capability mismatch fails before invoking domain operations. Unknown optional capabilities are not inferred from version numbers. Refuse unsafe fallback, including silently loading another RID, interpreting a Rust enum's memory, using a managed database provider, or changing query semantics after a capability mismatch.

## 6. Resource and concurrency obligations

Preserve [lifetime](../contracts/lifetime-v0.1.md), [callbacks](../contracts/callback-v0.1.md), [async](../contracts/async-v0.1.md) and [errors](../contracts/error-v0.1.md). The following are semantic requirements, not a second replacement ABI:

* A native object has one owning module and one destruction function. A C# SafeHandle protects physical lifetime; separate admission rules prevent mutable aliasing and post-close work.
* Borrowed buffers cannot survive their specified call/lease. A native async operation copies small request metadata or retains an explicit owner; it never stores an unpinned C# address or stack Span.
* Domain objects, operations and queued callbacks retain module/context owners until actual retirement. Public cancellation is not proof of native quiescence.
* A close deadline bounds caller waiting, not the lifetime of still-accessible native data. `ClosePending` retains owners and budget; a late native callback cannot access a freed GCHandle.
* Thread-affine resources are manipulated on their owning executor. Managed Task continuations do not confer Rust `Send`/`Sync` or permit moving an `Rc` between threads.

Every engine states its linearization points, reentrancy policy, outstanding-operation ceiling and failure quarantine. A producer must reserve budget before allocating/queuing work, including waiters and buffers retained after protocol acknowledgment.

## 7. Interface example — draft, not compiled

```c
/* Semantic sketch: actual field layouts come from accepted C-ABI-001. */
nw_status nw_engine_capabilities(nw_engine_handle e, nw_caps_out *out);
nw_status nw_operation_cancel(nw_operation_handle op);
nw_status nw_operation_take_result(nw_operation_handle op, nw_result_out *out);
nw_status nw_owned_buffer_release(nw_buffer_handle b);
```

These are illustrative names, not an instruction to duplicate an existing operation protocol. Domain-specific query builders and HTTP bodies stay in their Engine's ABI. Upstream enums, `Vec`, `String`, `Future` and trait objects are never ABI payloads. A function returning an error still specifies ownership of all inputs/partial outputs. Failure output fields are initialized, checked arithmetic precedes allocation, and panic containment does not promise recovery from abort, invalid pointers or corrupted native state.

## 8. Source and test mapping

Each normative adapter behavior maps to exact source symbols/ranges, observed upstream tests and NativeWeave obligations. Coverage is reported by mechanism, not repository download count. A public API's behavior may be unsupported, panicking or silently ignored for a backend; preserving user intent can require early rejection rather than a nominally faithful pass-through.

For SeaQuery, reuse native Expr/Condition/CRUD/CTE/window/dialect builders and SQLx execution. NativeWeave adds capability checks, fallible boundary value conversion, static DTO decoding and lifecycle control. For Server, reuse native parser, connection driver, scheduler and TLS; NativeWeave adds the foreign handler completion bridge and whole-lifetime budgets. These extra obligations are integration work, not proof that the engine must be rewritten.

## 9. Cost model and selection

Record FFI calls per operation, bytes copied in both directions, native and managed allocations/objects, metadata/query cache occupancy, runtime/thread counts, buffer retention, idle/peak RSS, cold start/package size, throughput and latency distribution. Compare a direct native binding, a batched binding and generated static fast paths before choosing an optimization. A batch adds a decoder and temporary command storage; a handle-per-node binding adds handles/calls. Neither is “free.”

Retain a pure native engine baseline and a feature-equivalent C# Native AOT baseline where applicable. Database's Rust mandate is a product boundary, not permission to assert it wins every metric. Server adoption requires a documented capability, cost or engineering advantage. A micro-FFI win does not establish end-to-end superiority.

## 10. Extension profiles and limits

Synchronous SIMD/codec operations may use borrowed spans for a call; streaming codecs need bounded chunks and state handles. GPU operations require device/fence ownership and asynchronous release. GUI/NSH may require main-thread dispatch and platform event-loop integration. These are capability combinations, not reasons to embed all domains in Core. R32/R33 still owe actual platform/source probes; this report does not certify GPU/mobile support.

## 11. Verification and implementation tasks

A17/A18 must exercise two genuinely different real engines, not two wrappers around the same synchronous mock. A01–A12 own layout/ownership/error/generation tests; A13–A16 build and clean consumption; A19/A20 model/property/fuzz/race checks; A21 benchmarks; A22 upgrade compatibility; A24 reproducible integration scaffolding. B01–B14 implement the mandatory Rust database profile, B17 the optional native Server bridge. Unrelated drafts remain parallel.

Production acceptance requires real Windows/Linux AOT consumer execution, compatible old/new binaries, wrong RID/ABI/feature negatives, overflow and malformed descriptor fuzzing, callback/close races, native sanitizers/model tools as applicable, long load/failure recovery and resource accounting. The recovered Linux SQLite example establishes only a bounded feasibility slice. An independent review must check source fidelity and whether added adaptation is smaller and safer than the avoided reimplementation.
