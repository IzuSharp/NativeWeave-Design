# R02 — Native AOT, trimming and supported application mechanisms

Research decision ready for independent review. This fills the missing canonical report; it reuses the successful Windows/Linux native-slice and logical-admission studies instead of relabeling them as new runs. The new `interop-completion` study adds actual Linux Native AOT callback, static serialization and negative dynamic-code experiments. Exact identities and limitations are in [evidence](evidence.json) and [coverage](coverage.json).

## Decision

The application surface uses normal modern C#, closed generic calls, static typed metadata, explicit codec/handler registration and framework-generated static native imports. Required Rust Database/ORM/Server functionality resides in precompiled native modules. Ordinary `dotnet build`/`dotnet run` do not require application Rust compilation; explicit-RID AOT publication is a separate supported consumption mode. No runtime expression compilation, emitted IL, reflection-only serializer fallback or arbitrary assembly-plugin discovery is required for normal use.

Native AOT is an application publication/analysis contract, not a ban on every reflection operation or every generic type. A reflected member must have preserved metadata and statically available code; generating unforeseen generic instantiations or dynamic executable code at runtime is not a valid fallback. Metadata-only dynamic database models are distinct from dynamic managed code: bounded entity/field descriptors can be passed to a precompiled Rust engine without generating native types.

## Source and executed evidence

dotnet/runtime v11.0.0 `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` exposes RequiresDynamicCodeAttribute for tools and implements LibraryImportGenerator as a Roslyn incremental generator. Annotation presence alone cannot establish that a consuming application is safe; the actual closed application must publish and execute. R01/D01 own current language/runtime support, including the separately verified .NET11 Runtime Async decision; this report does not repeat the old assumption that all Runtime Async is still preview.

The new `AotRestrictions` fixture publishes with `PublishAot=true` and runs with RuntimeFeature.IsDynamicCodeSupported false. A source-generated JsonSerializerContext roundtrips an explicit Record including non-ASCII text; closed int/string generics execute; reflection serializer fallback is disabled and rejected; constructing DynamicMethod throws PlatformNotSupportedException. Its one IL3050 suppression is tightly scoped to the intentional negative test and is not a product policy. Normal and AOT assertion counts are recorded separately.

The companion Completion fixture calls actual Rust through LibraryImport, receives UCO callbacks on a native worker, retains GCHandle roots through controlled GC and drains cancellation registrations. The first successful study and its exact source were preserved before the expanded study. Earlier Windows/Linux evidence already proves the limited native-slice package can load from a PackageReference and execute as AOT. Neither study proves a clean machine without Rust installed, complete product API reachability or every supported OS baseline.

## Failure/boundary analysis

| Mechanism | Required behavior |
|---|---|
| Unknown DTO/serializer type | Explicit registration or source metadata; deterministic unsupported error, no reflection fallback |
| Open generic entity/runtime type construction | Reject unsupported shape before native submission; close known generic paths statically |
| Missing native RID asset or symbol | Fail at package/load/ABI negotiation with module/RID identity; no managed engine fallback |
| Trimming warning | Fix root/annotation/design; no blanket warning suppression |
| New entity | Regenerate bounded C# metadata/mapping only; native binary hash unchanged |
| Reverse callback | Exact static blittable UCO signature; catch ordinary exceptions inside boundary; invalid ABI is a fatal-test concern |

Dynamic loading of **native** engine modules with a stable ABI is different from loading arbitrary new managed executable code. Initial modules remain loaded to process exit under D02; instance disposal does not imply hot unload. Target OS loaders, architecture and native dependencies still require real tests.

## Alternatives, cost and closure

Handwritten static metadata and optional SG metadata have identical runtime semantics. SG reduces boilerplate but adds deterministic build/IDE work; it cannot become the only query path. Runtime reflection discovery can be useful in tools but does not provide a portable AOT application contract. Large expression/LINQ translation and per-entity Rust code generation are rejected because they conflict with the declared application/native split, not because C# lacks those facilities.

D01/D03 specify the platform/build rules and pipeline. A10/A12/A14/A15/A16 must extend the research into all public imports, diagnostics and clean consumers; B10/B12 own optional metadata and typed result materialization. Those product obligations are not unresolved architecture questions. Current Windows replication of newly added negative cases is claimed only if a corresponding immutable CI result is present; Linux does not substitute for it.


## Supplemental invalid-UCO execution (2026-11-13)

The [isolated manifest](../../../../verification/interop-completion/uco-invalid-linux/result.json) records actual .NET11 normal and Native AOT publication followed by native invocation of an intentionally invalid char/bool `UnmanagedCallersOnly` callback with runtime marshalling enabled. Both child processes exited -6 with unhandled `InvalidProgramException`; `INVALID_CALLBACK_BODY_ENTERED` never appeared. This demonstrates that callback-body catch cannot repair an invalid signature. It does not establish all fail-fast variants or behavior of an outer managed catch. The normal blittable callback succeeds in the main fixture. Invalid-pointer fuzzing was not performed.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
